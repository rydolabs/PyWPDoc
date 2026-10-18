# -*- coding: utf-8 -*-
"""Offline regression, including both branches and failures without HWP COM."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import tempfile
import unittest
from unittest import mock

from verify_review_hwpx import (
    ALL_CASES, TEXT_EXPECTED, compare_review, inspect_hwpx, preflight, sha256
)
import run_review_windows

KIT=Path(__file__).resolve().parent


def fabricate_snapshot(mode: str):
    """Logical fixture only; NEVER creates or claims a native HWPX file."""
    source=inspect_hwpx(KIT/'SOURCE_TRACKED_V22.hwpx')
    result=deepcopy(source)
    result['revision_markers']=0
    result['revision_anchors']=[]
    for case,text in TEXT_EXPECTED[mode].items():
        cell=result['tables'][case]['cells'][1][1]
        cell['text']=text
        cell['paragraphs'][0]['text']=text
        cell['paragraphs'][0]['segments']=[{'text':text,'bold':False}]
        result['tables'][case]['rows'][1][1]=text
    result['tables']['T04_CHAR']['cells'][1][1]['paragraphs'][0]['segments']=[{
        'text':'BOLDME','bold':mode=='accept'}]
    result['tables']['T05_PARA']['cells'][1][1]['paragraphs'][0]['alignment']='CENTER' if mode=='accept' else 'JUSTIFY'
    return source,result


class FakeHwpSession:
    commands=[]
    def __init__(self): self.opened=None
    def open(self,path): self.opened=path
    def run(self,action): self.commands.append(action)
    def save(self,path):
        from shutil import copy2
        # Deliberately unresolved: a successful COM return is not a PASS.
        copy2(self.opened,path)
    def close(self): pass


class TestReviewRunner(unittest.TestCase):
    def test_preflight_original(self):
        pre=preflight(KIT/'SOURCE_TRACKED_V22.hwpx',KIT/'BASE_BEFORE_EDIT.hwpx')
        self.assertEqual(pre['status'],'PASS',pre)
        self.assertEqual(pre['header_revisions'],6)
        self.assertEqual(len(pre['tables']),10)

    def test_accept_logical_oracle(self):
        source,result=fabricate_snapshot('accept')
        report=compare_review(source,result,'accept')
        self.assertEqual(report['status'],'PASS',[r for r in report['checks'] if r['status']=='FAIL'])
        self.assertEqual(report['counts']['passed'],12)

    def test_reject_logical_oracle(self):
        source,result=fabricate_snapshot('reject')
        report=compare_review(source,result,'reject')
        self.assertEqual(report['status'],'PASS',[r for r in report['checks'] if r['status']=='FAIL'])

    def test_unresolved_marker_fails(self):
        source,result=fabricate_snapshot('accept')
        result['revision_markers']=1
        report=compare_review(source,result,'accept')
        self.assertEqual(report['status'],'FAIL')
        self.assertIn('P01_UNRESOLVED',[c['case'] for c in report['checks'] if c['status']=='FAIL'])

    def test_wrong_column_fails_without_blocking_other_cases(self):
        source,result=fabricate_snapshot('reject')
        result['tables']['S09_COL_DELETE']['rows'][0][0]='열 유지'
        report=compare_review(source,result,'reject')
        self.assertEqual(report['status'],'FAIL')
        self.assertEqual(sum(c['status']=='FAIL' for c in report['checks']),1)

    def test_unknown_bold_does_not_pass_reject(self):
        source,result=fabricate_snapshot('reject')
        result['tables']['T04_CHAR']['cells'][1][1]['paragraphs'][0]['segments'][0]['bold']=None
        self.assertEqual(compare_review(source,result,'reject')['status'],'FAIL')

    def test_action_return_without_effect_is_not_pass(self):
        with tempfile.TemporaryDirectory() as tmp:
            before=sha256(KIT/'SOURCE_TRACKED_V22.hwpx')
            FakeHwpSession.commands=[]
            data=run_review_windows.run(Path(tmp),driver_factory=FakeHwpSession)
            self.assertEqual(data['status'],'REVIEW')
            self.assertEqual(len(data['branches']),2)
            self.assertEqual([r['status'] for r in data['branches']],['FAIL','FAIL'])
            self.assertEqual(FakeHwpSession.commands,['TrackChangeApplyAll','TrackChangeCancelAll'])
            self.assertTrue(data['source_unchanged'])
            self.assertEqual(sha256(KIT/'SOURCE_TRACKED_V22.hwpx'),before)

    def test_fail_first_branch_continues_second(self):
        class FirstFails(FakeHwpSession):
            def run(self,action):
                if action=='TrackChangeApplyAll':raise RuntimeError('version does not support action')
                super().run(action)
        with tempfile.TemporaryDirectory() as tmp:
            data=run_review_windows.run(Path(tmp),driver_factory=FirstFails)
            self.assertEqual(len(data['branches']),2)
            self.assertEqual(data['branches'][0]['status'],'ERROR')
            self.assertEqual(data['branches'][1]['status'],'FAIL')

    def test_false_action_return_saves_both_branches_and_reports_fail(self):
        class ReturnsFalse(FakeHwpSession):
            def run(self,action):
                self.commands.append(action)
                return False
        with tempfile.TemporaryDirectory() as tmp:
            data=run_review_windows.run(Path(tmp),driver_factory=ReturnsFalse)
            self.assertEqual(data['status'],'REVIEW')
            self.assertEqual([b['status'] for b in data['branches']],['FAIL','FAIL'])
            self.assertEqual([b['action_return'] for b in data['branches']],[False,False])
            self.assertTrue((Path(tmp)/'ACCEPT_ALL_NATIVE.hwpx').exists())
            self.assertTrue((Path(tmp)/'REJECT_ALL_NATIVE.hwpx').exists())
            self.assertTrue(all('review' in b for b in data['branches']))

    def test_false_action_return_can_still_pass_when_semantics_pass(self):
        # Logical mock only: the saved file's hypothetical parsed content is
        # injected. This is NOT a native-Hancom acceptance/rejection fixture.
        original=inspect_hwpx(KIT/'SOURCE_TRACKED_V22.hwpx')
        _, accepted=fabricate_snapshot('accept')
        _, rejected=fabricate_snapshot('reject')
        class ReturnsFalse(FakeHwpSession):
            def run(self,action):return False
        def inspect_stub(path):
            name=Path(path).name
            if name=='ACCEPT_ALL_NATIVE.hwpx':return accepted
            if name=='REJECT_ALL_NATIVE.hwpx':return rejected
            return original
        with tempfile.TemporaryDirectory() as tmp:
            with mock.patch.object(run_review_windows,'inspect_hwpx',side_effect=inspect_stub):
                data=run_review_windows.run(Path(tmp),driver_factory=ReturnsFalse)
            self.assertEqual(data['status'],'PASS',data)
            self.assertEqual([b['status'] for b in data['branches']],['PASS','PASS'])
            self.assertEqual([b['action_return'] for b in data['branches']],[False,False])

    def test_save_false_return_is_logged_if_file_exists(self):
        class FalseSave(FakeHwpSession):
            def run(self,action):return False
            def save(self,path):
                super().save(path)
                return False
        with tempfile.TemporaryDirectory() as tmp:
            data=run_review_windows.run(Path(tmp),driver_factory=FalseSave)
            self.assertEqual([b['status'] for b in data['branches']],['FAIL','FAIL'])
            self.assertEqual([b['save_return'] for b in data['branches']],[False,False])
            self.assertTrue((Path(tmp)/'REJECT_ALL_NATIVE.hwpx').exists())

    def test_save_failure_is_local_to_branch(self):
        class FirstSaveFails(FakeHwpSession):
            def save(self,path):
                if path.name=='ACCEPT_ALL_NATIVE.hwpx':
                    raise RuntimeError('simulated save error')
                return super().save(path)
        with tempfile.TemporaryDirectory() as tmp:
            data=run_review_windows.run(Path(tmp),driver_factory=FirstSaveFails)
            self.assertEqual([b['status'] for b in data['branches']],['ERROR','FAIL'])
            self.assertTrue((Path(tmp)/'REJECT_ALL_NATIVE.hwpx').exists())

    def test_preflight_rejects_nontracked_input(self):
        bad=preflight(KIT/'BASE_BEFORE_EDIT.hwpx',KIT/'BASE_BEFORE_EDIT.hwpx')
        self.assertEqual(bad['status'],'FAIL')


if __name__=='__main__':
    unittest.main(verbosity=2)
