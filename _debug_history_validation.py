from pymongo import MongoClient
from datetime import UTC, datetime
from bson import ObjectId
from backend.app.models.schemas import AnalysisHistoryItem, AnalysisResponse

client = MongoClient('mongodb://127.0.0.1:27017')
db = client['musicgrowth']
uid = ObjectId('69c40bbbd3de40ee574db10f')

bad = 0
count = 0
for doc in db.song_analyses.find({'user_id': uid}).sort('created_at', -1).limit(100):
    count += 1
    sound_dna = doc.get('result', {}).get('sound_dna', {})
    parsed_result = None
    if doc.get('result'):
        try:
            parsed_result = AnalysisResponse(**doc['result'])
        except Exception:
            parsed_result = None

    try:
        AnalysisHistoryItem(
            id=str(doc['_id']),
            filename=doc.get('filename', 'upload'),
            segment_mode=doc.get('segment_mode', 'best'),
            mood=sound_dna.get('mood', 'Unknown'),
            production_style=sound_dna.get('production_style', 'Unknown'),
            created_at=doc.get('created_at', datetime.now(UTC)),
            result=parsed_result,
        )
    except Exception as exc:
        bad += 1
        print('BAD_DOC', doc.get('_id'), type(exc).__name__, str(exc))

print('checked', count, 'bad', bad)
