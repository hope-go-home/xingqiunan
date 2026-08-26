import json, os
base = r'D:\项目\智能任务自动化工作台\.lark-slides\project-defense\parts'
os.makedirs(base, exist_ok=True)
maps = {'pIt': ('brv', '03'), 'pIr': ('bMZ', '04'), 'pIO': ('bdq', '05'), 'pIl': ('bdu', '06'),
        'pIX': ('bIp', '07'), 'pIA': ('bGN', '08'), 'pId': ('bIs', '09'), 'pID': ('bOg', '10'),
        'pIj': ('bOm', '11'), 'pIo': ('blC', '12')}
for sid, (bid, num) in maps.items():
    repl = ('<shape type="text" topLeftX="820" topLeftY="518" width="60" height="20">'
            '<content fontSize="11" fontFamily="思源黑体" color="rgba(150,158,151,1)" textAlign="right">'
            '<p>%s</p></content></shape>' % num)
    parts = [{'action': 'block_replace', 'block_id': bid, 'replacement': repl}]
    p = os.path.join(base, sid + '.json')
    with open(p, 'w', encoding='utf-8') as f:
        json.dump(parts, f, ensure_ascii=False)
    print(sid, p)
