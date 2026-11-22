"""Judges see delivered questions without method identities or hidden expectations."""
import json
from pathlib import Path
import tempfile
import unittest
import run_gateway_replay as replay

class JudgePackets(unittest.TestCase):
    def test_source_only_questions_visible_and_missing_output_not_invented(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);context=root/'context.json'
            context.write_text(json.dumps([{'id':'source-secret','genre':'email','text':'Original source.','expected_label':'slop','target_spans':['hidden target'],'source':{'facts':'Known source fact.'}}]))
            methods={'method-secret':[{'id':'source-secret','text':'Original source.','pipelineResult':{'contextualReview':{'decision':'gap','findings':[{'question':'Which date is confirmed?','reason':'hidden rationale','quote':'Original source.'}]}}}],'missing-method':[{'id':'source-secret'}]}
            artifacts=replay.judge_packets(root,context,methods,['source-secret'])
            self.assertEqual(len(artifacts),2)
            packet=(root/'judge-packets/pass-1.json').read_text()
            for hidden in ['method-secret','missing-method','expected_label','hidden target','hidden rationale','source-secret']:self.assertNotIn(hidden,packet)
            row=json.loads(packet)[0]
            self.assertEqual(len(row['variants']),1)
            self.assertEqual(row['variants']['A']['author_questions'],['Which date is confirmed?'])
            self.assertEqual(row['source_notes'],{'facts':'Known source fact.'})

if __name__=='__main__':unittest.main()
