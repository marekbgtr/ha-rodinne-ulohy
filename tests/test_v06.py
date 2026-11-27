"""Weekend boundaries, exact reward refunds, and saved approval notifications."""
import unittest
from datetime import datetime
from copy import deepcopy
from test_engine import Engine, RuleError
import test_controller


def date(s):
    return datetime.fromisoformat(s + '+01:00')


class WeekendTests(unittest.TestCase):
    def setUp(self):
        self.e=Engine()
        self.now=date('2026-11-26T18:00:00')
        self.e.save_person({'name':'A'},self.now,'admin')
        self.a=next(iter(self.e.s['people']))
        self.e.save_task({'name':'Škola','frequency':'weekend','due':'19:00','cutoff':'22:00','points':3,'late_points':1,'penalty':2},self.now,'admin')

    def tick(self, stamp):
        now=date(stamp);self.e.tick(now);return now

    def test_one_occurrence_across_weekend_and_new_next_friday(self):
        self.assertFalse(self.e.s['occurrences'])
        now=self.tick('2026-11-27T00:00:00');o=next(iter(self.e.s['occurrences'].values()))
        self.assertEqual(o['due'],'2026-11-29T19:00:00+01:00')
        self.e.complete({'person':self.a,'occurrence':o['id']},now,'child')
        self.tick('2026-11-29T21:00:00');self.assertEqual(len(self.e.s['occurrences']),1)
        self.assertEqual(self.e.balance(self.a),3)
        now=self.tick('2026-11-30T00:00:00');self.assertFalse(self.e.current(o,now))
        self.tick('2026-12-04T00:00:00');self.assertEqual(len(self.e.s['occurrences']),2)

    def test_sunday_late_and_undo_exact(self):
        now=self.tick('2026-11-29T19:01:00');o=next(iter(self.e.s['occurrences']))
        args={'person':self.a,'occurrence':o}
        self.e.complete(args,now,'child');self.assertEqual(self.e.balance(self.a),1)
        self.e.undo(args,now,'admin');self.assertEqual(self.e.balance(self.a),0)
        self.e.approve_full(args,now,'admin');self.assertEqual(self.e.balance(self.a),3)

    def test_penalty_once_and_cannot_complete_after_cutoff(self):
        now=self.tick('2026-11-29T22:00:00');oid=next(iter(self.e.s['occurrences']))
        self.e.tick(now);self.assertEqual(self.e.balance(self.a),-2)
        with self.assertRaises(RuleError):self.e.complete({'person':self.a,'occurrence':oid},now,'child')
        self.tick('2026-11-30T10:00:00');self.assertEqual(self.e.balance(self.a),-2)

    def test_exact_due_gets_full_points_and_restore(self):
        now=self.tick('2026-11-29T19:00:00');oid=next(iter(self.e.s['occurrences']))
        self.e.complete({'person':self.a,'occurrence':oid},now,'child')
        restored=Engine(deepcopy(self.e.s));restored.tick(now)
        self.assertEqual(restored.balance(self.a),3)

    def test_sunday_creation_has_no_previous_weekend_penalty(self):
        e=Engine();now=date('2026-11-29T18:00:00');e.save_person({'name':'A'},now,'admin')
        e.save_task({'name':'Škola','frequency':'weekend','points':3,'penalty':2},now,'admin')
        self.assertEqual(len(e.s['occurrences']),1)
        self.assertEqual(e.balance(next(iter(e.s['people']))),0)


class ReturnRewardTests(unittest.TestCase):
    def setUp(self):
        self.e=Engine();self.now=date('2026-11-27T18:00:00')
        for name in ['A','B']:self.e.save_person({'name':name},self.now,'admin')
        self.a,self.b=self.e.s['people']
        for p in [self.a,self.b]:self.e.adjust({'person':p,'delta':10,'reason':'Test'},self.now,'admin')

    def test_shared_refund_exact_and_idempotent(self):
        self.e.save_reward({'name':'Výlet','cost':10,'shared':True},self.now,'admin');rid=next(iter(self.e.s['rewards']))
        for p,n in [(self.a,6),(self.b,4)]:self.e.contribute_reward({'person':p,'reward':rid,'amount':n},self.now,'child')
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'approve'},self.now,'admin')
        args={'request':req}
        with self.assertRaises(RuleError):self.e.apply('return_reward',args,self.now,'child',False)
        for _ in range(2):self.e.apply('return_reward',args,self.now,'admin',True)
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[10,10])
        self.e.contribute_reward({'person':self.a,'reward':rid,'amount':5},self.now,'child')
        self.assertEqual(len(self.e.s['requests']),2)

    def test_personal_refund_and_new_request(self):
        self.e.save_reward({'name':'Kniha','cost':3},self.now,'admin');rid=next(iter(self.e.s['rewards']))
        self.e.request_reward({'person':self.a,'reward':rid},self.now,'child');req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'approve'},self.now,'admin')
        self.e.return_reward({'request':req},self.now,'admin');self.assertEqual(self.e.balance(self.a),10)
        self.e.request_reward({'person':self.a,'reward':rid},self.now,'child');self.assertEqual(self.e.balance(self.a),7)


class ApprovalNotifications(unittest.IsolatedAsyncioTestCase):
    asyncSetUp = test_controller.TransactionTests.asyncSetUp
    send = test_controller.TransactionTests.send
    async def test_pending_task_event_after_save_once_and_banner_cleared(self):
        from test_controller import NOW
        occ=self.c.engine.s['occurrences'][self.oid];occ['task']['approval']=True
        def event(name,payload):
            self.assertEqual(name,'family_quests_task_approval_requested')
            self.assertTrue(self.c.store.saved['occurrences'][self.oid]['members'][self.a]['submitted'])
        self.c.hass.bus.async_fire.side_effect=event
        await self.send();await self.send()
        self.c.hass.bus.async_fire.assert_called_once()
        self.assertEqual(self.c.hass.services.async_call.call_args.args[1],'create')
        await self.send('approve',admin=True,rid='approve01')
        self.assertEqual(self.c.hass.services.async_call.call_args.args[1],'dismiss')

    async def test_no_notification_on_failed_task_save(self):
        self.c.engine.s['occurrences'][self.oid]['task']['approval']=True
        self.c.store.fail=True
        self.c.hass.bus.async_fire.reset_mock();self.c.hass.services.async_call.reset_mock()
        with self.assertRaises(OSError):await self.send()
        self.c.hass.bus.async_fire.assert_not_called();self.c.hass.services.async_call.assert_not_called()

    async def test_repeated_task_creates_one_event_per_attempt(self):
        from test_controller import NOW
        from datetime import timedelta
        e=self.c.engine;e.s['tasks'].clear();e.s['occurrences'].clear()
        e.save_task({'name':'Stôl','frequency':'repeat','approval':True,'repeat_gap':0},NOW,'admin')
        self.oid=next(iter(e.s['occurrences']))
        await self.send(rid='repeat01')
        await self.c.transact('complete',{'person':self.a,'occurrence':self.oid},actor='user',request_id='repeat02',expected_version=e.s['version'],now=NOW+timedelta(seconds=3))
        events=[c.args for c in self.c.hass.bus.async_fire.call_args_list if c.args[0]=='family_quests_task_approval_requested']
        self.assertEqual(len(events),2)
        self.assertNotEqual(events[0][1]['attempt_id'],events[1][1]['attempt_id'])

    async def test_refund_failed_save_restores_approved_and_balance(self):
        from test_controller import NOW
        e=self.c.engine;e.adjust({'person':self.a,'delta':10,'reason':'Test'},NOW,'admin')
        e.save_reward({'name':'Kniha','cost':3},NOW,'admin');rid=next(iter(e.s['rewards']))
        e.request_reward({'person':self.a,'reward':rid},NOW,'child');req=next(iter(e.s['requests']))
        e.decide_reward({'request':req,'decision':'approve'},NOW,'admin');before=deepcopy(e.s)
        self.c.store.fail=True
        with self.assertRaises(OSError):await self.send('return_reward',request=req,admin=True,rid='refund01')
        self.assertEqual(e.s,before)
        self.c.store.fail=False
        await self.send('return_reward',request=req,admin=True,rid='refund01')
        self.assertEqual(e.balance(self.a),10)
