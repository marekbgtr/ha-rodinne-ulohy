"""Behavior tests runnable with Python's standard library only."""
import importlib.util
from pathlib import Path
import unittest
from datetime import datetime, timedelta
from copy import deepcopy
import json

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('fq_engine', ROOT / 'custom_components/family_quests/engine.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
Engine, RuleError = module.Engine, module.RuleError


def at(hour='18:00', day='2026-11-17', offset='+01:00'):
    return datetime.fromisoformat(day + 'T' + hour + ':00' + offset)


class EngineTests(unittest.TestCase):
    def setUp(self):
        self.e = Engine()
        for name in ['Maty', 'Momo']:
            self.e.save_person({'name': name}, at(), 'admin')
        self.a, self.b = self.e.s['people']
        self.task(mode='independent')

    def task(self, **kw):
        self.e.s['tasks'].clear()
        self.e.s['occurrences'].clear()
        self.e.save_task({'name': 'Pyžamo', 'points': 2, 'late_points': 1,
                          'penalty': 2, **kw}, at(), 'admin')
        self.tid = next(iter(self.e.s['tasks']))
        self.oid = self.tid + ':2026-11-17'

    def do(self, action='complete', pid=None, when=None, **kw):
        self.e.apply(action, {'occurrence': self.oid, 'person': pid or self.a, **kw},
                     when or at(), 'admin', action != 'complete')

    def test_independent_completion_and_exact_undo(self):
        self.do(); self.do(pid=self.b)
        self.do('undo')
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]], [0,2])
        self.assertTrue(self.e.s['occurrences'][self.oid]['members'][self.b]['award'])

    def test_late_undo_only_reclaims_actual_award(self):
        self.do(when=at('20:00')); self.assertEqual(self.e.balance(self.a),1)
        self.do('undo',when=at('20:01')); self.assertEqual(self.e.balance(self.a),0)

    def test_repeated_complete_and_undo(self):
        self.do(); self.do(); self.assertEqual(self.e.balance(self.a),2)
        self.do('undo'); self.do('undo'); self.assertEqual(self.e.balance(self.a),0)
        self.do(); self.assertEqual(self.e.balance(self.a),2)

    def test_zero_point_completion_is_reversible(self):
        self.task(points=0,late_points=0)
        self.do(); self.assertTrue(self.e.s['occurrences'][self.oid]['members'][self.a]['award'])
        self.do('undo'); self.assertEqual(self.e.balance(self.a),0)

    def test_approval_uses_submission_time(self):
        self.task(approval=True)
        self.do(); self.assertEqual(self.e.balance(self.a),0)
        self.do('approve',when=at('23:00'))
        self.assertEqual(self.e.balance(self.a),2)

    def test_pending_approval_not_penalized(self):
        self.task(approval=True); self.do()
        self.e.tick(at('23:00'))
        self.assertEqual(self.e.balance(self.a),0)
        self.assertEqual(self.e.balance(self.b),-2)

    def test_deadline_boundary(self):
        self.do(when=at('19:45')); self.assertEqual(self.e.balance(self.a),2)
        self.do(pid=self.b,when=at('19:46')); self.assertEqual(self.e.balance(self.b),1)

    def test_cutoff_boundary(self):
        with self.assertRaises(RuleError): self.do(when=at('22:00'))

    def test_penalty_applied_once_across_restart(self):
        self.e.tick(at('22:00'))
        self.e=Engine(json.loads(json.dumps(self.e.s)))
        self.e.tick(at('23:00'))
        self.assertEqual(self.e.balance(self.a),-2)

    def test_exemption_reverses_penalty(self):
        self.e.tick(at('23:00')); self.do('exempt',when=at('23:01'),reason='Choroba')
        self.e.tick(at('23:02'))
        self.assertEqual(self.e.balance(self.a),0)
        self.assertEqual(self.e.balance(self.b),-2)

    def test_exemption_blocks_completion(self):
        self.do('exempt')
        with self.assertRaises(RuleError): self.do()

    def test_first_winner_and_reopen(self):
        self.task(mode='first'); self.do()
        with self.assertRaises(RuleError): self.do(pid=self.b)
        self.do('undo'); self.do(pid=self.b)
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[0,2])

    def test_first_never_penalizes_non_winner(self):
        self.task(mode='first'); self.e.tick(at('23:00'))
        self.assertEqual(self.e.balance(self.a),0)

    def test_first_approval_reserves_winner(self):
        self.task(mode='first',approval=True); self.do()
        with self.assertRaises(RuleError): self.do(pid=self.b)
        self.do('undo'); self.do(pid=self.b); self.do('approve',pid=self.b)
        self.assertEqual(self.e.balance(self.b),2)

    def test_together_rewards_only_when_all_complete(self):
        self.task(mode='together'); self.do(); self.assertEqual(self.e.balance(self.a),0)
        self.do(pid=self.b); self.assertEqual(self.e.balance(self.a),2)
        self.do('undo'); self.assertEqual(self.e.balance(self.b),0)
        self.assertTrue(self.e.s['occurrences'][self.oid]['members'][self.b]['confirmed'])
        self.do(); self.assertEqual(self.e.balance(self.b),2)

    def test_together_split_preserves_total(self):
        self.task(mode='together',points=5,split=True)
        self.do(); self.do(pid=self.b)
        self.assertEqual(self.e.balance(self.a)+self.e.balance(self.b),5)
        self.do('undo'); self.assertEqual(self.e.balance(self.a)+self.e.balance(self.b),0)

    def test_together_late_shared_pool(self):
        self.task(mode='together',points=5,late_points=3,split=True)
        self.do(); self.do(pid=self.b,when=at('20:00'))
        self.assertEqual(self.e.balance(self.a)+self.e.balance(self.b),3)

    def test_together_exempt_one(self):
        self.task(mode='together'); self.do(); self.do('exempt',pid=self.b)
        self.assertEqual(self.e.balance(self.a),2)
        self.assertEqual(self.e.balance(self.b),0)

    def test_rotation_one_person_per_scheduled_day(self):
        self.task(mode='rotation')
        self.assertEqual(list(self.e.s['occurrences'][self.oid]['members']),[self.a])
        self.e.tick(at(day='2026-11-18'))
        self.assertEqual(list(self.e.s['occurrences'][self.tid+':2026-11-18']['members']),[self.b])

    def test_weekdays_and_once(self):
        self.task(days=[0])  # Tuesday is not scheduled.
        self.assertNotIn(self.oid,self.e.s['occurrences'])
        self.task(frequency='once',date='2026-11-18')
        self.assertNotIn(self.oid,self.e.s['occurrences'])
        self.e.tick(at(day='2026-11-18')); self.e.tick(at(day='2026-11-19'))
        self.assertEqual(len(self.e.s['occurrences']),1)

    def test_single_person_assignment(self):
        self.task(everyone=False,people=[self.b])
        self.assertEqual(list(self.e.s['occurrences'][self.oid]['members']),[self.b])

    def test_offline_catchup_and_idempotence(self):
        self.e.tick(at()); self.e.tick(at('23:00',day='2026-11-19'))
        self.assertEqual(self.e.balance(self.a),-6)
        self.e.tick(at('23:00',day='2026-11-19')); self.assertEqual(self.e.balance(self.a),-6)

    def test_long_outage_notice(self):
        self.e.tick(at()); self.e.tick(at('23:00',day='2027-02-01'))
        self.assertTrue(self.e.s['notices'])
        self.assertLessEqual(len(self.e.s['occurrences']),33)

    def test_dst_utc_deadline(self):
        e=Engine(); e.save_person({'name':'A'},at(day='2026-03-28'),'a')
        e.save_task({'name':'Test'},at(day='2026-03-28'),'a')
        e.tick(at(day='2026-03-29',offset='+02:00'))
        deadlines=[o['due'] for o in e.s['occurrences'].values()]
        self.assertTrue(any(x.endswith('+01:00') for x in deadlines))
        self.assertTrue(any(x.endswith('+02:00') for x in deadlines))

    def test_person_symbol_preserves_balance(self):
        self.do(); self.e.set_symbol({'person':self.a,'symbol':'🐴','unit':'Koníky'},at(),'a')
        self.assertEqual(self.e.balance(self.a),2)

    def test_deactivation_excuses_today(self):
        self.e.save_person({'id':self.a,'name':'Maty','active':False},at(),'a')
        self.e.tick(at('23:00')); self.assertEqual(self.e.balance(self.a),0)

    def test_edit_after_activity_freezes_occurrence(self):
        self.do(); task=deepcopy(self.e.s['tasks'][self.tid]);task['points']=9
        self.e.save_task(task,at(),'a')
        self.do(pid=self.b);self.assertEqual(self.e.balance(self.b),2)
        self.e.tick(at(day='2026-11-18'))
        self.assertEqual(self.e.s['occurrences'][self.tid+':2026-11-18']['task']['points'],9)

    def test_edit_untouched_updates_today(self):
        task=deepcopy(self.e.s['tasks'][self.tid]);task['points']=9
        self.e.save_task(task,at(),'a');self.do();self.assertEqual(self.e.balance(self.a),9)

    def reward(self, **kw):
        self.e.save_reward({'name':'Rozprávka','cost':2,**kw},at(),'a')
        return list(self.e.s['rewards'])[-1]

    def test_reward_reserves_once_and_refunds(self):
        self.do(); rid=self.reward()
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),0)
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        self.assertEqual(self.e.balance(self.a),2)

    def test_reward_approval_no_second_debit(self):
        self.do();rid=self.reward();self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'approve'},at(),'a')
        self.assertEqual(self.e.balance(self.a),0)

    def test_reward_insufficient_balance(self):
        rid=self.reward()
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')

    def test_linked_reward_once_and_cancel_on_undo(self):
        rid=self.reward(kind='task',task=self.tid)
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.do();self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'approve'},at(),'a')
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.do('undo');self.assertEqual(self.e.s['requests'][req]['status'],'cancelled')
        self.assertEqual(self.e.balance(self.a),0)

    def test_linked_reward_ontime_requirement(self):
        rid=self.reward(kind='task',task=self.tid,on_time=True);self.do(when=at('20:00'))
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at('20:00'),'a')

    def test_reverse_manual_exact_once(self):
        self.e.adjust({'person':self.a,'delta':10},at(),'a');eid=self.e.s['ledger'][-1]['id']
        self.e.reverse_adjustment({'entry':eid},at(),'a');self.e.reverse_adjustment({'entry':eid},at(),'a')
        self.assertEqual(self.e.balance(self.a),0)

    def test_admin_actions_forbidden_to_child(self):
        for action in ['save_person','save_task','save_reward','adjust','undo','approve','exempt','decide_reward','reverse_adjustment']:
            with self.subTest(action=action),self.assertRaises(RuleError):
                self.e.apply(action,{},at(),'child',False)

    def test_bad_inputs_rejected(self):
        for bad in [{'points':True},{'points':-1},{'mode':'invalid'},{'due':'23:00','cutoff':'20:00'},{'late_points':3},{'days':[]},{'everyone':False,'people':[]}]:
            with self.subTest(bad=bad),self.assertRaises(RuleError):
                self.e.save_task({'name':'Invalid','points':2,**bad},at(),'a')

    def test_undo_after_cutoff_reassesses_penalty(self):
        self.do();self.do('undo',when=at('23:00'))
        self.assertEqual(self.e.balance(self.a),-2)
        self.do('exempt',when=at('23:01'));self.assertEqual(self.e.balance(self.a),0)

    def test_restart_roundtrip_same_snapshot(self):
        self.do(); s=self.e.snapshot(at(),True)
        self.assertEqual(Engine(json.loads(json.dumps(self.e.s))).snapshot(at(),True),s)

    def test_zero_cost_task_reward_even_with_negative_balance(self):
        self.e.adjust({'person':self.a,'delta':-10},at(),'a');self.do()
        rid=self.reward(kind='task',task=self.tid)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),-8)

    def test_combined_reward_requires_task_even_with_enough_points(self):
        rid=self.reward(kind='task_points',task=self.tid,cost=2)
        self.e.adjust({'person':self.a,'delta':10},at(),'a')
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),10)
        self.assertFalse(self.e.s['requests'])

    def test_combined_reward_requires_points_even_with_task_done(self):
        self.do(); rid=self.reward(kind='task_points',task=self.tid,cost=3)
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),2)
        self.assertFalse(self.e.s['requests'])

    def test_combined_reward_debit_and_approval_only_once(self):
        self.do();rid=self.reward(kind='task_points',task=self.tid,cost=2)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        req=next(iter(self.e.s['requests']))
        self.assertEqual(self.e.balance(self.a),0)
        self.e.decide_reward({'request':req,'decision':'approve'},at(),'a')
        self.e.decide_reward({'request':req,'decision':'approve'},at(),'a')
        self.assertEqual(self.e.balance(self.a),0)
        self.e.adjust({'person':self.a,'delta':10},at(),'a')
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at(),'a')

    def test_combined_reject_refunds_exactly_and_can_retry(self):
        self.do();rid=self.reward(kind='task_points',task=self.tid,cost=2)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        self.assertEqual(self.e.balance(self.a),2)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),0)

    def test_combined_undo_task_refunds_cost_and_reclaims_award(self):
        self.e.adjust({'person':self.a,'delta':10},at(),'a')
        self.do();rid=self.reward(kind='task_points',task=self.tid,cost=3)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.assertEqual(self.e.balance(self.a),9)
        self.do('undo');self.do('undo')
        self.assertEqual(self.e.balance(self.a),10)
        req=next(iter(self.e.s['requests'].values()))
        self.assertEqual(req['status'],'cancelled')
        self.assertEqual(self.e.balance(self.b),0)

    def test_combined_ontime_and_approval_required(self):
        self.task(approval=True);self.do(when=at('20:00'))
        rid=self.reward(kind='task_points',task=self.tid,cost=1,on_time=True)
        self.e.adjust({'person':self.a,'delta':10},at(),'a')
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at('20:01'),'a')
        self.do('approve',when=at('20:02'))
        with self.assertRaises(RuleError): self.e.request_reward({'person':self.a,'reward':rid},at('20:03'),'a')

    def test_combined_validates_task_and_cost(self):
        for data in [{'task':'missing','cost':2},{'task':self.tid,'cost':-1}]:
            with self.assertRaises(RuleError): self.reward(kind='task_points',**data)

    def test_combined_saved_reward_edits_do_not_change_reservation(self):
        self.do();rid=self.reward(kind='task_points',task=self.tid,cost=2)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.e.save_reward({'id':rid,'name':'New','kind':'task_points','task':self.tid,'cost':10},at(),'a')
        self.e=Engine(json.loads(json.dumps(self.e.s)))
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        self.assertEqual(self.e.balance(self.a),2)

    def test_stats_counts_ontime_late_waiting_exempt_and_missed(self):
        self.do(); self.do(pid=self.b,when=at('20:00'))
        sa=self.e.weekly_stats(self.a,at('23:00'))[0]
        sb=self.e.weekly_stats(self.b,at('23:00'))[0]
        self.assertEqual((sa['assigned'],sa['completed'],sa['on_time'],sa['earned'],sa['rate']),(1,1,1,2,100))
        self.assertEqual((sb['late'],sb['earned']),(1,1))
        self.assertEqual(sa['days'][1]['completed'],1)
        self.assertEqual(sa['perfect_days'],0)  # today is not yet a closed day
        self.e.tick(at(day='2026-11-18'))
        later=self.e.weekly_stats(self.a,at(day='2026-11-18'))[0]
        self.assertEqual(later['perfect_days'],1)
        self.assertEqual(later['open'],1)
        self.assertTrue(any(b['label']=='Hotový deň' for b in later['badges']))

    def test_stats_exemption_excluded_from_denominator(self):
        self.do('exempt')
        stats=self.e.weekly_stats(self.a,at('23:00'))[0]
        self.assertEqual(stats['assigned'],0)
        self.assertEqual(stats['exempt'],1)
        self.assertIsNone(stats['rate'])

    def test_stats_first_loser_not_penalized(self):
        self.task(mode='first');self.do()
        stats=self.e.weekly_stats(self.b,at('23:00'))[0]
        self.assertEqual(stats['assigned'],0)
        self.assertEqual(stats['missed'],0)
        self.assertIsNone(stats['rate'])

    def test_stats_waiting_and_missed_distinct(self):
        self.task(approval=True);self.do();self.e.tick(at('23:00'))
        a=self.e.weekly_stats(self.a,at('23:00'))[0]
        b=self.e.weekly_stats(self.b,at('23:00'))[0]
        self.assertEqual((a['waiting'],a['missed'],a['completed']),(1,0,0))
        self.assertEqual((b['waiting'],b['missed'],b['penalties']),(0,1,2))

    def test_stats_undo_removes_completion_points_and_badge(self):
        self.do();self.do('undo')
        stats=self.e.weekly_stats(self.a,at())[0]
        self.assertEqual(stats['completed'],0)
        self.assertEqual(stats['earned'],0)
        self.assertEqual(stats['badges'],[])
        self.assertEqual(stats['open'],1)

    def test_stats_ledger_categories_after_refunds(self):
        self.do();self.e.adjust({'person':self.a,'delta':10},at(),'a')
        self.e.adjust({'person':self.a,'delta':-1},at(),'a')
        rid=self.reward(cost=3);self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        w=self.e.weekly_stats(self.a,at())[0]
        self.assertEqual((w['earned'],w['bonus'],w['penalties'],w['spent'],w['net']),(2,10,1,3,8))
        req=next(iter(self.e.s['requests']))
        self.e.decide_reward({'request':req,'decision':'reject'},at(),'a')
        w=self.e.weekly_stats(self.a,at())[0]
        self.assertEqual((w['spent'],w['net']),(0,11))

    def test_stats_monday_boundaries_and_eight_weeks(self):
        self.do()
        weeks=self.e.weekly_stats(self.a,at(day='2026-11-23'))
        self.assertEqual(len(weeks),8)
        self.assertEqual(weeks[0]['start'],'2026-11-23')
        self.assertEqual(weeks[0]['completed'],0)
        self.assertEqual(weeks[1]['start'],'2026-11-16')
        self.assertEqual(weeks[1]['completed'],1)
        self.assertEqual(weeks[1]['earned'],2)

    def test_stats_empty_profile_no_fake_success(self):
        self.e.save_person({'name':'Rodič'},at(),'a')
        pid=list(self.e.s['people'])[-1]
        w=self.e.weekly_stats(pid,at())[0]
        self.assertIsNone(w['rate']);self.assertEqual(w['badges'],[])
        self.assertTrue(w['days'][6]['future'])

    def test_group_order_persists_and_unknown_new_group_appends(self):
        self.e.save_task({'name':'Ranné','group':'Ráno'},at(),'a')
        self.e.save_task({'name':'Večerné','group':'Večer'},at(),'a')
        self.e.apply('set_group_order',{'groups':['Večer','Ráno','Úlohy']},at(),'admin',True)
        restored=Engine(json.loads(json.dumps(self.e.s)))
        self.assertEqual(restored.groups(),['Večer','Ráno','Úlohy'])
        restored.save_task({'name':'Nové','group':'Po škole'},at(),'a')
        self.assertEqual(restored.groups(),['Večer','Ráno','Úlohy','Po škole'])

    def test_group_order_validation_and_permission(self):
        for value in [['Ráno','Ráno'],[''],[123],'Ráno']:
            with self.assertRaises(RuleError):self.e.set_group_order({'groups':value},at(),'a')
        with self.assertRaises(RuleError):self.e.apply('set_group_order',{'groups':[]},at(),'child',False)

    def test_stats_group_totals_and_order(self):
        self.e.save_task({'name':'Ranné','group':'Ráno'},at(),'a')
        self.e.set_group_order({'groups':['Ráno','Úlohy']},at(),'a');self.do()
        w=self.e.weekly_stats(self.a,at())[0]
        self.assertEqual([g['name'] for g in w['groups']],['Ráno','Úlohy'])
        self.assertEqual(sum(g['assigned'] for g in w['groups']),w['assigned'])
        self.assertEqual(sum(g['completed'] for g in w['groups']),w['completed'])

    def reset(self, when=None, start='tomorrow'):
        self.e.apply('reset_progress',{'confirmation':'VYMAZAT HISTORIU','backup_confirmed':True,'start':start},when or at(),'admin',True)

    def test_reset_requires_admin_phrase_and_backup(self):
        good={'confirmation':'VYMAZAT HISTORIU','backup_confirmed':True}
        before=deepcopy(self.e.s)
        for args,admin in [(good,False),({'confirmation':'ano','backup_confirmed':True},True),({'confirmation':'VYMAZAT HISTORIU'},True)]:
            with self.assertRaises(RuleError):self.e.apply('reset_progress',args,at(),'user',admin)
            self.assertEqual(before,self.e.s)

    def test_reset_preserves_definitions_and_clears_progress(self):
        self.do();rid=self.reward();self.e.request_reward({'person':self.a,'reward':rid},at(),'a')
        self.e.set_group_order({'groups':['Úlohy']},at(),'a')
        defs={key:deepcopy(self.e.s[key]) for key in ['people','tasks','rewards','group_order']}
        self.e.s['request_ids']=['prior-request']
        self.reset()
        for key,val in defs.items():self.assertEqual(self.e.s[key],val)
        self.assertEqual(self.e.balance(self.a),0)
        self.assertFalse(self.e.s['ledger']);self.assertFalse(self.e.s['requests']);self.assertFalse(self.e.s['occurrences'])
        self.assertEqual(self.e.s['request_ids'],['prior-request'])
        self.assertEqual(self.e.s['tracking_start'],'2026-11-18')

    def test_reset_tomorrow_does_not_recreate_today_even_on_edit(self):
        self.reset();task=deepcopy(self.e.s['tasks'][self.tid])
        self.e.save_task(task,at('20:00'),'a');self.e.tick(at('23:00'))
        self.assertFalse(self.e.s['occurrences']);self.assertEqual(self.e.balance(self.a),0)
        self.e=Engine(json.loads(json.dumps(self.e.s)))
        self.e.tick(at(day='2026-11-18'))
        self.assertIn(self.tid+':2026-11-18',self.e.s['occurrences'])
        self.assertNotIn(self.oid,self.e.s['occurrences'])

    def test_reset_today_no_retroactive_penalty(self):
        self.e.tick(at('23:00'));self.assertEqual(self.e.balance(self.a),-2)
        self.reset(when=at('23:10'),start='today')
        self.e.tick(at('23:20'))
        self.assertFalse(self.e.s['occurrences']);self.assertEqual(self.e.balance(self.a),0)
        self.assertEqual(self.e.weekly_stats(self.a,at('23:20'))[0]['assigned'],0)

    def test_reset_today_keeps_not_yet_closed_tasks(self):
        self.reset(start='today')
        self.assertIn(self.oid,self.e.s['occurrences'])
        self.do();self.assertEqual(self.e.balance(self.a),2)

    def test_backward_compatible_without_new_settings(self):
        old=deepcopy(self.e.s)
        for key in ['group_order','tracking_start','tracking_started_at']:old.pop(key,None)
        snapshot=Engine(old).snapshot(at(),True)
        self.assertEqual(snapshot['group_order'],['Úlohy'])
        self.assertIsNone(snapshot['tracking_start'])
        self.assertEqual(len(snapshot['statistics'][self.a]),8)


    def test_weekly_any_day_once_and_next_monday(self):
        self.task(frequency='weekly')
        self.oid=next(iter(self.e.s['occurrences']))
        self.do(when=at(day='2026-11-20'))
        self.do(when=at(day='2026-11-22'))
        self.assertEqual(self.e.balance(self.a),2)
        self.assertEqual(len(self.e.s['occurrences']),1)
        self.e.tick(at('00:00',day='2026-11-23'))
        self.assertEqual(len(self.e.s['occurrences']),2)
        self.assertEqual(self.e.balance(self.b),-2)
        self.assertFalse(self.e.current(self.e.s['occurrences'][self.oid],at(day='2026-11-23')))
        self.assertEqual(self.e.weekly_stats(self.a,at(day='2026-11-23'))[1]['completed'],1)

    def test_weekly_boundary_and_penalty_day(self):
        self.task(frequency='weekly');self.oid=next(iter(self.e.s['occurrences']))
        self.e.tick(at('00:00',day='2026-11-23'))
        with self.assertRaises(RuleError): self.do(when=at('00:00',day='2026-11-23'))
        self.assertEqual(self.e.s['ledger'][0]['day'],'2026-11-22')
        self.e.tick(at('01:00',day='2026-11-23'))
        self.assertEqual(self.e.balance(self.a),-2)

    def test_ongoing_no_penalty_and_late_completion(self):
        self.task(frequency='ongoing');self.oid=next(iter(self.e.s['occurrences']))
        self.e.tick(at(day='2026-12-03'))
        self.assertEqual(self.e.balance(self.a),0)
        self.do(when=at(day='2026-12-03'))
        self.assertEqual(self.e.balance(self.a),2)
        self.assertEqual(len(self.e.s['occurrences']),1)
        stats=self.e.weekly_stats(self.a,at(day='2026-12-03'))
        self.assertEqual((stats[0]['completed'],stats[0]['earned']),(1,2))
        self.assertEqual(stats[1]['assigned'],0)
        self.do('undo',when=at(day='2026-12-04'))
        self.assertEqual(self.e.balance(self.a),0)

    def test_long_term_available_early_and_no_duplicates(self):
        self.task(frequency='once',date='2026-12-01');self.oid=next(iter(self.e.s['occurrences']))
        self.do(when=at(day='2026-11-20'))
        self.e.tick(at(day='2026-12-01'))
        self.assertEqual(len(self.e.s['occurrences']),1)
        self.assertEqual(self.e.balance(self.a),2)
        self.assertEqual(self.e.s['ledger'][0]['day'],'2026-11-20')
        self.assertEqual(self.e.weekly_stats(self.a,at(day='2026-11-20'))[0]['completed'],1)

    def test_weekly_reward_link_and_undo(self):
        self.task(frequency='weekly');self.oid=next(iter(self.e.s['occurrences']))
        self.e.save_reward({'name':'Rozprávka','kind':'task','task':self.tid,'on_time':True},at(),'admin')
        rid=next(iter(self.e.s['rewards']))
        self.do(when=at(day='2026-11-20'))
        self.assertEqual(self.e.snapshot(at(day='2026-11-21'))['reward_links'][self.a][rid],self.oid)
        self.e.request_reward({'person':self.a,'reward':rid},at(day='2026-11-21'),'child')
        self.do('undo',when=at(day='2026-11-21'))
        self.assertEqual(next(iter(self.e.s['requests'].values()))['status'],'cancelled')
        self.assertEqual(self.e.balance(self.a),0)

    def test_weekly_rotation(self):
        self.task(frequency='weekly',mode='rotation')
        self.e.tick(at(day='2026-11-23'))
        occurrences=list(self.e.s['occurrences'].values())
        self.assertEqual(list(occurrences[0]['members']),[self.a])
        self.assertEqual(list(occurrences[1]['members']),[self.b])

    def test_weekly_reset_midweek(self):
        self.task(frequency='weekly')
        self.e.reset_progress({'confirmation':'VYMAZAT HISTORIU','backup_confirmed':True,'start':'today'},at(),'admin')
        self.e.tick(at())
        self.assertEqual(len(self.e.s['occurrences']),1)
        self.assertEqual(self.e.balance(self.a),0)

    def test_no_deadline_together_first_and_approval(self):
        for mode in ['together','first','independent']:
            self.task(frequency='ongoing',mode=mode,approval=True)
            self.oid=next(iter(self.e.s['occurrences']))
            self.do(); self.do('approve')
            if mode=='together': self.do(pid=self.b);self.do('approve',pid=self.b)
            self.assertTrue(self.e.s['occurrences'][self.oid]['members'][self.a]['award'])
            self.do('undo')
            self.assertIsNone(self.e.s['occurrences'][self.oid]['members'][self.a]['award'])


    def test_unexempt_restores_open_task(self):
        self.do('exempt');self.do('unexempt');self.do()
        self.assertEqual(self.e.balance(self.a),2)

    def test_unexempt_restores_penalty_once(self):
        self.e.tick(at('23:00'));self.do('exempt',when=at('23:01'))
        self.assertEqual(self.e.balance(self.a),0)
        self.do('unexempt',when=at('23:02'));self.do('unexempt',when=at('23:03'))
        self.assertEqual(self.e.balance(self.a),-2)
        self.do('exempt',when=at('23:04'));self.do('unexempt',when=at('23:05'))
        self.assertEqual(self.e.balance(self.a),-2)

    def test_unexempt_reopens_group_and_refunds_reward(self):
        self.task(mode='together',split=True)
        self.do();self.do('exempt',pid=self.b)
        self.assertEqual(self.e.balance(self.a),2)
        rid=self.reward(kind='task',task=self.tid)
        self.e.request_reward({'person':self.a,'reward':rid},at(),'child')
        self.do('unexempt',pid=self.b)
        self.assertEqual(self.e.balance(self.a),0)
        self.assertEqual(next(iter(self.e.s['requests'].values()))['status'],'cancelled')
        self.do(pid=self.b)
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[1,1])

    def test_full_points_topup_undo_no_double_award(self):
        self.do(when=at('20:00'));self.assertEqual(self.e.balance(self.a),1)
        self.do('approve_full',when=at('20:01'));self.do('approve_full',when=at('20:02'))
        self.assertEqual(self.e.balance(self.a),2)
        stats=self.e.weekly_stats(self.a,at('20:02'))[0]
        self.assertEqual((stats['earned'],stats['late']),(2,1))
        self.do('undo',when=at('20:03'));self.assertEqual(self.e.balance(self.a),0)
        self.do(when=at('20:04'));self.assertEqual(self.e.balance(self.a),1)

    def test_full_points_after_cutoff_returns_penalty(self):
        self.e.tick(at('23:00'));self.assertEqual(self.e.balance(self.a),-2)
        self.do('approve_full',when=at('23:01'))
        self.assertEqual(self.e.balance(self.a),2)
        self.do('undo',when=at('23:02'));self.assertEqual(self.e.balance(self.a),-2)

    def test_full_points_pending_and_group_recalculation(self):
        self.task(mode='together',split=False,approval=True)
        self.do(when=at('20:00'));self.do(pid=self.b,when=at('20:00'))
        self.do('approve',when=at('20:01'));self.do('approve',pid=self.b,when=at('20:01'))
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[1,1])
        self.do('approve_full',when=at('20:02'))
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[2,1])

    def test_full_points_split_pool_needs_all_late_members_approved(self):
        self.task(mode='together',split=True,points=6,late_points=2)
        self.do(when=at('20:00'));self.do(pid=self.b,when=at('20:00'))
        self.do('approve_full',when=at('20:02'))
        self.assertEqual(self.e.balance(self.a),1)
        self.do('approve_full',pid=self.b,when=at('20:03'))
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[3,3])

    def test_full_points_race_cannot_steal_winner(self):
        self.task(mode='first');self.do()
        with self.assertRaises(RuleError):self.do('approve_full',pid=self.b)

    def test_new_parent_actions_reject_child(self):
        for action,data in [('unexempt',{}),('approve_full',{}),('set_statistics',{'enabled':True})]:
            with self.assertRaises(RuleError):
                self.e.apply(action,{'occurrence':self.oid,'person':self.a,**data},at(),'child',False)

    def test_statistics_visibility_individual_and_persistent(self):
        self.assertNotIn(self.a,self.e.snapshot(at())['statistics'])
        self.e.apply('set_statistics',{'person':self.a,'enabled':True},at(),'admin',True)
        snap=Engine(self.e.s).snapshot(at())
        self.assertIn(self.a,snap['statistics']);self.assertNotIn(self.b,snap['statistics'])
        self.assertEqual(len(self.e.snapshot(at(),True)['statistics']),2)
        self.e.set_symbol({'person':self.b,'symbol':'🐴','unit':'Koníky','show_statistics':True},at(),'child')
        self.assertNotIn(self.b,self.e.snapshot(at())['statistics'])

    def test_repeat_limit_gap_and_daily_reset(self):
        self.task(frequency='repeat',repeat_limit=2,repeat_gap=5)
        self.do(when=at('08:00'))
        with self.assertRaises(RuleError):self.do(when=at('08:01'))
        self.do(when=at('12:00'))
        with self.assertRaises(RuleError):self.do(when=at('18:00'))
        self.assertEqual(self.e.balance(self.a),4)
        self.e.tick(at('08:00',day='2026-11-18'));self.oid=self.tid+':2026-11-18'
        self.do(when=at('08:00',day='2026-11-18'));self.assertEqual(self.e.balance(self.a),6)

    def test_repeat_exact_undo_of_one_attempt_and_reapprove(self):
        self.task(frequency='repeat',approval=True)
        self.do(when=at('08:00'));self.do(when=at('12:00'))
        records=self.e.s['occurrences'][self.oid]['members'][self.a]['attempts']
        self.do('approve',attempt=records[0]['id']);self.do('approve',attempt=records[1]['id'])
        self.do('undo',attempt=records[0]['id']);self.do('undo',attempt=records[0]['id'])
        self.assertEqual(self.e.balance(self.a),2)
        with self.assertRaises(RuleError):self.do('approve',attempt=records[0]['id'])
        self.assertEqual(self.e.weekly_stats(self.a,at())[0]['completed'],1)

    def test_repeat_goal_penalty_pending_and_undo(self):
        self.task(frequency='repeat',repeat_goal=2,approval=True)
        self.do(when=at('08:00'));self.do(when=at('12:00'))
        records=self.e.s['occurrences'][self.oid]['members'][self.a]['attempts']
        later=at('00:01',day='2026-11-18');self.e.tick(later)
        self.assertEqual(self.e.balance(self.a),0) # Pending claims count towards target.
        self.assertEqual(self.e.balance(self.b),-2)
        self.do('undo',attempt=records[0]['id'],when=later)
        self.assertEqual(self.e.balance(self.a),-2)
        self.do('exempt',when=later);self.assertEqual(self.e.balance(self.a),0)
        self.do('unexempt',when=later);self.assertEqual(self.e.balance(self.a),-2)

    def test_repeat_optional_never_penalized(self):
        self.task(frequency='repeat',repeat_goal=0,penalty=10)
        self.e.tick(at('00:01',day='2026-11-18'))
        self.assertEqual(self.e.balance(self.a),0)
        self.assertEqual(self.e.weekly_stats(self.a,at('23:59'))[0]['assigned'],0)

    def test_repeat_goal_statistics(self):
        self.task(frequency='repeat',repeat_goal=3)
        self.do(when=at('08:00'));self.do(when=at('12:00'))
        stats=self.e.weekly_stats(self.a,at())[0]
        self.assertEqual((stats['completed'],stats['assigned'],stats['earned'],stats['open']),(2,3,4,1))
        self.e.tick(at('00:01',day='2026-11-18'))
        stats=self.e.weekly_stats(self.a,at('00:01',day='2026-11-18'))[0]
        self.assertEqual(stats['missed'],1)

    def test_repeat_reward_once_daily_and_undo_last(self):
        self.task(frequency='repeat')
        rid=self.reward(kind='task',task=self.tid)
        self.do(when=at('08:00'));self.do(when=at('12:00'))
        records=self.e.s['occurrences'][self.oid]['members'][self.a]['attempts']
        self.e.request_reward({'person':self.a,'reward':rid},at(),'child')
        self.do('undo',attempt=records[0]['id'])
        self.assertEqual(next(iter(self.e.s['requests'].values()))['status'],'pending')
        self.do('undo',attempt=records[1]['id'])
        self.assertEqual(next(iter(self.e.s['requests'].values()))['status'],'cancelled')

    def test_repeat_validation_and_clock_boundary(self):
        with self.assertRaises(RuleError):self.task(frequency='repeat',repeat_limit=2,repeat_goal=3)
        with self.assertRaises(RuleError):self.task(frequency='repeat',mode='together')
        self.task(frequency='repeat',repeat_gap=0,repeat_limit=0)
        self.do(when=at('23:59'))
        with self.assertRaises(RuleError):self.do(when=at('23:59'))
        with self.assertRaises(RuleError):self.do(when=at('00:00',day='2026-11-18'))

    def test_repeat_restore_and_rotation(self):
        self.task(frequency='repeat',mode='rotation')
        self.do();saved=deepcopy(self.e.s);self.e=Engine(saved)
        self.e.tick(at('08:00',day='2026-11-18'))
        self.assertEqual(self.e.balance(self.a),2)
        self.assertEqual(list(self.e.s['occurrences'][self.tid+':2026-11-18']['members']),[self.b])


    def test_real_010_state_fixture_upgrade(self):
        old=json.loads((ROOT/'tests/fixtures/state_010.json').read_text())
        e=Engine(old);now=at(day='2026-11-21');e.tick(now)
        pid=next(iter(e.s['people']));oid=next(iter(e.s['occurrences']))
        self.assertEqual(e.balance(pid),1)
        self.assertEqual(e.s['ledger'],old['ledger'])
        self.assertFalse(e.snapshot(now)['people'][0]['show_statistics'])
        e.apply('undo',{'person':pid,'occurrence':oid},now,'admin',True)
        self.assertEqual(e.balance(pid),0)

    def pool(self, cost=10):
        rid=self.reward(kind='points',shared=True,cost=cost)
        self.e.adjust({'person':self.a,'delta':20},at(),'parent')
        self.e.adjust({'person':self.b,'delta':20},at(),'parent')
        return rid

    def contribute(self, rid, pid, amount):
        self.e.apply('contribute_reward',{'person':pid,'reward':rid,'amount':amount},at(),'child',False)

    def test_pool_two_people_approval_charges_once(self):
        rid=self.pool();self.contribute(rid,self.a,6);self.contribute(rid,self.b,4)
        req=self.e.shared_request(rid)
        self.assertEqual(req['status'],'pending')
        self.assertEqual(self.e.contributions(req),{self.a:6,self.b:4})
        self.e.decide_reward({'request':req['id'],'decision':'approve'},at(),'parent')
        self.e.decide_reward({'request':req['id'],'decision':'approve'},at(),'parent')
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[14,16])
        self.assertEqual(self.e.weekly_stats(self.a,at())[0]['spent'],6)
        self.assertEqual(req['status'],'approved')

    def test_pool_reject_exact_refund_idempotent(self):
        rid=self.pool();self.contribute(rid,self.a,6);self.contribute(rid,self.b,4)
        req=self.e.shared_request(rid)
        self.e.decide_reward({'request':req['id'],'decision':'reject'},at(),'parent')
        self.e.decide_reward({'request':req['id'],'decision':'reject'},at(),'parent')
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[20,20])
        self.assertEqual(self.e.weekly_stats(self.a,at())[0]['spent'],0)

    def test_pool_withdraw_only_own_and_can_rejoin(self):
        rid=self.pool();self.contribute(rid,self.a,3);self.contribute(rid,self.a,2);self.contribute(rid,self.b,2)
        req=self.e.shared_request(rid)
        self.e.withdraw_contribution({'person':self.a,'request':req['id']},at(),'child')
        self.e.withdraw_contribution({'person':self.a,'request':req['id']},at(),'child')
        self.assertEqual(self.e.contributions(req),{self.b:2})
        self.assertEqual([self.e.balance(p) for p in [self.a,self.b]],[20,18])
        self.contribute(rid,self.a,8)
        self.assertEqual(req['status'],'pending')
        with self.assertRaises(RuleError):self.e.withdraw_contribution({'person':self.a,'request':req['id']},at(),'child')

    def test_pool_overfund_insufficient_and_invalid_amount(self):
        rid=self.pool();self.contribute(rid,self.a,8)
        before=deepcopy(self.e.s)
        for amount in [3,0,-1,True,1.5]:
            with self.assertRaises(RuleError):self.contribute(rid,self.b,amount)
            self.assertEqual(self.e.s,before)
        self.e.adjust({'person':self.b,'delta':-20},at(),'parent')
        with self.assertRaises(RuleError):self.contribute(rid,self.b,1)

    def test_pool_cannot_bypass_or_approve_partial(self):
        rid=self.pool()
        with self.assertRaises(RuleError):self.e.request_reward({'person':self.a,'reward':rid},at(),'child')
        self.contribute(rid,self.a,3);req=self.e.shared_request(rid)
        with self.assertRaises(RuleError):self.e.decide_reward({'request':req['id'],'decision':'approve'},at(),'parent')
        with self.assertRaises(RuleError):self.e.apply('decide_reward',{'request':req['id'],'decision':'reject'},at(),'child',False)
        self.e.decide_reward({'request':req['id'],'decision':'reject'},at(),'parent')
        self.assertEqual(self.e.balance(self.a),20)

    def test_pool_edit_locked_price_and_disabled_refund(self):
        rid=self.pool();self.contribute(rid,self.a,3);req=self.e.shared_request(rid)
        with self.assertRaises(RuleError):self.e.save_reward({'id':rid,'name':'Zmena','shared':True,'cost':11},at(),'parent')
        self.e.save_reward({'id':rid,'name':'Zmena','shared':True,'cost':10,'active':False},at(),'parent')
        with self.assertRaises(RuleError):self.contribute(rid,self.b,1)
        self.e.withdraw_contribution({'person':self.a,'request':req['id']},at(),'child')
        self.assertEqual(self.e.balance(self.a),20)
        self.assertEqual(req['status'],'cancelled')

    def test_pool_snapshot_keeps_old_active_pool(self):
        rid=self.pool();self.contribute(rid,self.a,3);req=self.e.shared_request(rid)
        for i in range(101):
            self.e.s['requests']['dummy'+str(i)]={'id':'dummy'+str(i),'status':'approved'}
        snap=Engine(self.e.s).snapshot(at())
        actual=next(r for r in snap['requests'] if r['id']==req['id'])
        self.assertEqual(actual['funded'],3)
        self.assertEqual(actual['contributors'],{self.a:3})

    def test_pool_new_round_and_validation(self):
        rid=self.pool();self.contribute(rid,self.a,10);req=self.e.shared_request(rid)
        with self.assertRaises(RuleError):self.contribute(rid,self.b,1)
        self.e.decide_reward({'request':req['id'],'decision':'approve'},at(),'parent')
        self.contribute(rid,self.b,5)
        self.assertNotEqual(req['id'],self.e.shared_request(rid)['id'])
        with self.assertRaises(RuleError):self.reward(kind='task',task=self.tid,shared=True)
        with self.assertRaises(RuleError):self.reward(shared=True,cost=0)


if __name__=='__main__':unittest.main()


