import unittest
from copy import deepcopy
from datetime import timedelta
from test_engine import Engine, RuleError, at
import test_controller


class NotificationSettings(unittest.IsolatedAsyncioTestCase):
    asyncSetUp=test_controller.TransactionTests.asyncSetUp
    send=test_controller.TransactionTests.send

    async def test_toggle_off_dismisses_and_keeps_mobile_events(self):
        await self.send('set_notifications',enabled=False,admin=True,rid='settings01')
        self.assertFalse(self.c.engine.s['ha_notifications'])
        self.c.engine.s['occurrences'][self.oid]['task']['approval']=True
        await self.send(rid='complete01')
        self.assertEqual(self.c.hass.bus.async_fire.call_args.args[0],'family_quests_task_approval_requested')
        self.assertEqual(self.c.hass.services.async_call.call_args.args[1],'dismiss')
        await self.send('set_notifications',enabled=True,admin=True,rid='settings02')
        self.assertEqual(self.c.hass.services.async_call.call_args.args[1],'create')

    async def test_setting_requires_admin_and_survives_restart(self):
        with self.assertRaises(ValueError):await self.send('set_notifications',enabled=False)
        await self.send('set_notifications',enabled=False,admin=True)
        restored=type(self.c.engine)(self.c.store.saved)
        self.assertFalse(restored.snapshot(test_controller.NOW,True)['ha_notifications'])


class PendingApprovalTests(unittest.TestCase):
    def setUp(self):
        self.e=Engine();self.now=at()
        self.e.save_person({'name':'A'},self.now,'admin');self.p=next(iter(self.e.s['people']))
        self.e.save_task({'name':'Úloha','approval':True,'points':3,'late_points':1},self.now,'admin')
        self.o=next(iter(self.e.s['occurrences']))
        self.args={'kind':'task','person':self.p,'occurrence':self.o,'submitted_at':self.now.isoformat()}
        self.e.complete(self.args,self.now,'child')

    def test_approval_exact_once_and_permission(self):
        with self.assertRaises(RuleError):self.e.apply('approve_pending',self.args,self.now,'child',False)
        for _ in range(2):self.e.apply('approve_pending',self.args,self.now,'admin',True)
        self.assertEqual(self.e.balance(self.p),3)

    def test_old_notification_cannot_approve_new_completion(self):
        self.e.undo(self.args,self.now,'admin')
        self.e.complete(self.args,self.now+timedelta(seconds=5),'child')
        with self.assertRaises(RuleError):self.e.approve_pending(self.args,self.now,'admin')
        self.assertEqual(self.e.balance(self.p),0)

    def test_cancelled_reward_cannot_be_approved(self):
        self.e.adjust({'person':self.p,'delta':10,'reason':'Test'},self.now,'admin')
        self.e.save_reward({'name':'Kniha','cost':3},self.now,'admin');rid=next(iter(self.e.s['rewards']))
        self.e.request_reward({'reward':rid,'person':self.p},self.now,'child');req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'reject'},self.now,'admin')
        with self.assertRaises(RuleError):self.e.approve_pending({'kind':'reward','request':req},self.now,'admin')
        self.assertEqual(self.e.balance(self.p),10)

    def test_late_task_keeps_late_points(self):
        self.e.undo(self.args,self.now,'admin');now=at('21:00')
        self.e.complete(self.args,now,'child');self.args['submitted_at']=now.isoformat()
        self.e.approve_pending(self.args,now,'admin');self.assertEqual(self.e.balance(self.p),1)
