"""Frozen metadata-only batching must not reveal both variants of a source."""
import hashlib
import json
import unittest
import order

class OrderChecks(unittest.TestCase):
    def fixture(self):
        original=['sealed-015','sealed-016','sealed-025','sealed-026','sealed-033','sealed-034','sealed-037','sealed-038','sealed-041','sealed-042','sealed-043','sealed-044']
        ids=['sealed-042','sealed-015','sealed-026','sealed-044','sealed-038','sealed-016','sealed-033','sealed-043','sealed-034','sealed-041','sealed-037','sealed-025']
        groups={id:group for index,group in enumerate(['source-20','source-25','source-29','source-31','source-33','source-34']) for id in original[index*2:index*2+2]}
        metadata={'seed':20261122,'batch_size':4,'panel':{'draft_ids':ids,'batches':[ids[i:i+4] for i in range(0,12,4)],'shuffle_attempts':3,'order_sha256':hashlib.sha256(json.dumps(ids,separators=(',',':')).encode()).hexdigest()}}
        return metadata,{'source_group_by_id':groups,'original_draft_order':original},original

    def test_exact_first_valid_permutation(self):
        metadata,groups,original=self.fixture()
        self.assertEqual(order.validate(metadata,groups,'panel',original),metadata['panel']['draft_ids'])

    def test_missing_member_is_not_replaced(self):
        metadata,groups,original=self.fixture()
        with self.assertRaises(ValueError):order.validate(metadata,groups,'panel',original[:-1])

    def test_pair_leak_is_rejected_even_with_matching_hash(self):
        metadata,groups,original=self.fixture();metadata['panel']['draft_ids']=original
        metadata['panel']['batches']=[original[i:i+4] for i in range(0,12,4)]
        metadata['panel']['order_sha256']=hashlib.sha256(json.dumps(original,separators=(',',':')).encode()).hexdigest()
        with self.assertRaisesRegex(ValueError,'Paired variants'):order.validate(metadata,groups,'panel',original)

if __name__=='__main__':unittest.main()
