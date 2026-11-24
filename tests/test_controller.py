"""HA adapter transaction tests with in-memory HA/storage substitutes.

These exercise the real controller, but are not a running HA installation.
"""
import asyncio
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import types
import unittest
from datetime import datetime
from unittest.mock import patch, Mock

ROOT=Path(__file__).resolve().parents[1]/'custom_components/family_quests'


def load_controller():
    package=types.ModuleType('fq_test');package.__path__=[str(ROOT)]
    fake_storage=types.ModuleType('homeassistant.helpers.storage')
    fake_storage.Store=FakeStore
    fake_dispatcher=types.ModuleType('homeassistant.helpers.dispatcher')
    fake_dispatcher.async_dispatcher_send=lambda *a:None
    with patch.dict(sys.modules, {'fq_test':package,'homeassistant.helpers.storage':fake_storage,
                                 'homeassistant.helpers.dispatcher':fake_dispatcher}):
        spec=importlib.util.spec_from_file_location('fq_test.controller',ROOT/'controller.py')
        mod=importlib.util.module_from_spec(spec);spec.loader.exec_module(mod)
    return mod.Controller


class FakeStore:
    def __init__(self,*args):self.saved=None;self.fail=False
    async def async_load(self):return deepcopy(self.saved)
    async def async_save(self,state):
        await asyncio.sleep(0)
        if self.fail:raise OSError('disk full')
        self.saved=deepcopy(state)


Controller=load_controller()
NOW=datetime.fromisoformat('2026-11-17T18:00:00+01:00')


class TransactionTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        hass=types.SimpleNamespace(config=types.SimpleNamespace(time_zone='Europe/Bratislava'), bus=types.SimpleNamespace(async_fire=Mock()))
        entry=types.SimpleNamespace(entry_id='test',data={})
        self.c=Controller(hass,entry)
        e=self.c.engine
        e.save_person({'name':'A'},NOW,'admin');e.save_person({'name':'B'},NOW,'admin')
        self.a,self.b=e.s['people']
        e.save_task({'name':'Test','mode':'first','points':2},NOW,'admin')
        self.oid=next(iter(e.s['occurrences']))
        await self.c.transact(now=NOW)

    async def send(self, action='complete', pid=None, rid='request01', version=None, admin=False, **data):
        return await self.c.transact(action,{'person':pid or self.a,'occurrence':self.oid,**data},
            actor='user',admin=admin,request_id=rid,
            expected_version=self.c.engine.s['version'] if version is None else version,now=NOW)

    async def test_race_only_one_winner(self):
        version=self.c.engine.s['version']
        results=await asyncio.gather(self.send(version=version),self.send(pid=self.b,rid='request02',version=version),return_exceptions=True)
        self.assertEqual(sum(isinstance(r,dict) for r in results),1)
        self.assertEqual(self.c.engine.balance(self.a)+self.c.engine.balance(self.b),2)

    async def test_replayed_request_not_double_adjust(self):
        v=self.c.engine.s['version']
        await self.send('adjust',admin=True,delta=2,version=v)
        await self.send('adjust',admin=True,delta=2,version=v)
        self.assertEqual(self.c.engine.balance(self.a),2)

    async def test_failed_save_rolls_back_and_retry_succeeds(self):
        before=deepcopy(self.c.engine.s);self.c.store.fail=True
        with self.assertRaises(OSError):await self.send()
        self.assertEqual(self.c.engine.s,before)
        self.c.store.fail=False;await self.send()
        self.assertEqual(self.c.engine.balance(self.a),2)

    async def test_unauthorized_mutation_rolls_back(self):
        before=deepcopy(self.c.engine.s)
        with self.assertRaises(ValueError):await self.send('adjust',delta=20)
        self.assertEqual(self.c.engine.s,before)

    async def test_stale_undo_cannot_reverse_new_completion(self):
        await self.send();stale=self.c.engine.s['version']
        await self.send('undo',rid='request02',admin=True)
        await self.send(rid='request03')
        with self.assertRaises(ValueError):await self.send('undo',rid='request04',admin=True,version=stale)
        self.assertEqual(self.c.engine.balance(self.a),2)

    async def test_durable_state_restores_exactly(self):
        await self.send()
        restored=type(self.c.engine)(self.c.store.saved)
        self.assertEqual(restored.s,self.c.engine.s)
        self.assertEqual(restored.balance(self.a),2)

    async def test_no_change_does_not_increment_version(self):
        v=self.c.engine.s['version'];await self.c.transact(now=NOW)
        self.assertEqual(self.c.engine.s['version'],v)

    def prepare_reward(self):
        self.c.engine.save_reward({'name':'Rozprávka','kind':'task','task':self.oid.split(':')[0]},NOW,'admin')
        return next(iter(self.c.engine.s['rewards']))

    async def test_reward_event_after_save_and_no_duplicate_on_retry(self):
        reward=self.prepare_reward();await self.send()
        v=self.c.engine.s['version']
        def on_event(name,payload):
            self.assertIn(payload['request_id'],self.c.store.saved['requests'])
        self.c.hass.bus.async_fire.side_effect=on_event
        await self.send('request_reward',reward=reward,rid='reward01',version=v)
        await self.send('request_reward',reward=reward,rid='reward01',version=v)
        await self.c.transact(now=NOW)
        self.c.hass.bus.async_fire.assert_called_once()
        name,payload=self.c.hass.bus.async_fire.call_args.args
        self.assertEqual(name,'family_quests_reward_requested')
        self.assertEqual(payload['person_name'],'A')
        self.assertEqual(payload['reward_name'],'Rozprávka')
        self.assertEqual(payload['cost'],0)

    async def test_failed_reward_save_does_not_emit_event(self):
        reward=self.prepare_reward();await self.send();self.c.store.fail=True
        with self.assertRaises(OSError):await self.send('request_reward',reward=reward,rid='reward01')
        self.c.hass.bus.async_fire.assert_not_called()
        self.assertFalse(self.c.engine.s['requests'])

    async def test_denied_reward_does_not_emit_event(self):
        reward=self.prepare_reward()
        with self.assertRaises(ValueError):await self.send('request_reward',reward=reward,rid='reward01')
        self.c.hass.bus.async_fire.assert_not_called()

    async def test_event_failure_preserves_saved_request(self):
        reward=self.prepare_reward();await self.send()
        self.c.hass.bus.async_fire.side_effect=RuntimeError('bus unavailable')
        with self.assertLogs('fq_test.controller',level='ERROR'):
            await self.send('request_reward',reward=reward,rid='reward01')
        self.assertEqual(len(self.c.store.saved['requests']),1)
        self.assertEqual(self.c.engine.s,self.c.store.saved)

    async def test_failed_reset_rolls_back_entire_history(self):
        await self.send();before=deepcopy(self.c.engine.s);self.c.store.fail=True
        with self.assertRaises(OSError):
            await self.send('reset_progress',rid='reset001',admin=True,confirmation='VYMAZAT HISTORIU',backup_confirmed=True,start='tomorrow')
        self.assertEqual(self.c.engine.s,before)

    async def test_replayed_reset_does_not_erase_new_manual_points(self):
        await self.send()
        v=self.c.engine.s['version']
        await self.send('reset_progress',rid='reset001',admin=True,version=v,confirmation='VYMAZAT HISTORIU',backup_confirmed=True,start='tomorrow')
        await self.send('adjust',rid='adjust01',admin=True,delta=5)
        await self.send('reset_progress',rid='reset001',admin=True,version=v,confirmation='VYMAZAT HISTORIU',backup_confirmed=True,start='tomorrow')
        self.assertEqual(self.c.engine.balance(self.a),5)
        self.c.hass.bus.async_fire.assert_not_called()


    async def test_full_approval_failed_save_rolls_back(self):
        before=deepcopy(self.c.engine.s);self.c.store.fail=True
        with self.assertRaises(OSError):await self.send('approve_full',admin=True)
        self.assertEqual(self.c.engine.s,before)

    async def test_repeated_click_replay_and_storage_restore(self):
        e=self.c.engine;e.s['tasks'].clear();e.s['occurrences'].clear()
        e.save_task({'name':'Stôl','frequency':'repeat','repeat_gap':0,'points':2},NOW,'admin')
        self.oid=next(iter(e.s['occurrences']))
        v=e.s['version'];await self.send(version=v);await self.send(version=v)
        self.assertEqual(len(e.s['occurrences'][self.oid]['members'][self.a]['attempts']),1)
        restored=type(e)(self.c.store.saved)
        self.assertEqual(restored.balance(self.a),2)

    async def test_repeat_undo_failure_rolls_back_record_and_points(self):
        e=self.c.engine;e.s['tasks'].clear();e.s['occurrences'].clear()
        e.save_task({'name':'Stôl','frequency':'repeat','points':2},NOW,'admin')
        self.oid=next(iter(e.s['occurrences']));await self.send()
        attempt=e.s['occurrences'][self.oid]['members'][self.a]['attempts'][0]['id']
        before=deepcopy(e.s);self.c.store.fail=True
        with self.assertRaises(OSError):await self.send('undo',rid='undo0001',admin=True,attempt=attempt)
        self.assertEqual(e.s,before)


    def prepare_pool(self):
        e=self.c.engine
        e.adjust({'person':self.a,'delta':10},NOW,'admin')
        e.adjust({'person':self.b,'delta':10},NOW,'admin')
        e.save_reward({'name':'Výlet','shared':True,'cost':10},NOW,'admin')
        return next(iter(e.s['rewards']))

    async def test_pool_event_only_when_fully_funded_and_not_replayed(self):
        rid=self.prepare_pool()
        await self.send('contribute_reward',reward=rid,amount=6,rid='pool0001')
        self.c.hass.bus.async_fire.assert_not_called()
        v=self.c.engine.s['version']
        await self.send('contribute_reward',pid=self.b,reward=rid,amount=4,rid='pool0002',version=v)
        await self.send('contribute_reward',pid=self.b,reward=rid,amount=4,rid='pool0002',version=v)
        self.c.hass.bus.async_fire.assert_called_once()
        payload=self.c.hass.bus.async_fire.call_args.args[1]
        self.assertTrue(payload['shared'])
        self.assertEqual(payload['contributors'],{self.a:6,self.b:4})
        self.assertEqual(payload['person_name'],'A, B')
        self.assertEqual(self.c.store.saved['requests'][payload['request_id']]['status'],'pending')

    async def test_pool_failed_final_contribution_rolls_back(self):
        rid=self.prepare_pool()
        await self.send('contribute_reward',reward=rid,amount=6,rid='pool0001')
        before=deepcopy(self.c.engine.s);self.c.store.fail=True
        with self.assertRaises(OSError):await self.send('contribute_reward',pid=self.b,reward=rid,amount=4,rid='pool0002')
        self.assertEqual(self.c.engine.s,before)
        self.c.hass.bus.async_fire.assert_not_called()

    async def test_pool_racing_contributions_cannot_overfund(self):
        rid=self.prepare_pool();v=self.c.engine.s['version']
        result=await asyncio.gather(self.send('contribute_reward',reward=rid,amount=7,rid='pool0001',version=v),self.send('contribute_reward',pid=self.b,reward=rid,amount=7,rid='pool0002',version=v),return_exceptions=True)
        self.assertEqual(sum(isinstance(r,dict) for r in result),1)
        req=self.c.engine.shared_request(rid)
        self.assertEqual(sum(self.c.engine.contributions(req).values()),7)


if __name__=='__main__':unittest.main()


