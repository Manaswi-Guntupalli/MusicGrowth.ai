from pymongo import MongoClient
from bson import ObjectId
import math

client = MongoClient('mongodb://127.0.0.1:27017')
db = client['musicgrowth']
uid = ObjectId('69c40bbbd3de40ee574db10f')

def has_non_finite(value):
    if isinstance(value, float):
        return not math.isfinite(value)
    if isinstance(value, dict):
        return any(has_non_finite(v) for v in value.values())
    if isinstance(value, list):
        return any(has_non_finite(v) for v in value)
    return False

bad = []
for doc in db.song_analyses.find({'user_id': uid}):
    res = doc.get('result', {})
    if has_non_finite(res):
        bad.append(str(doc.get('_id')))

print('non_finite_docs', len(bad))
if bad:
    print('\n'.join(bad))
