#!/usr/bin/env python3
import json

with open(r'C:\Users\86159\.claude\skills\start-my-day\merged.json', encoding='utf-8') as f:
    d = json.load(f)

# 找论文列表
papers = d.get('filtered', d.get('papers', d.get('top_papers', [])))
print(f'Total papers in merged.json: {len(papers)}')
print(f'Keys: {list(d.keys())}')
for i, p in enumerate(papers, 1):
    score = p.get('scores', {})
    overall = score.get('overall', score.get('recommendation', '?'))
    print(f'{i}. [{p.get("year","?")}] {p["title"][:70]}')
    print(f'   cite={p.get("citation_count",0)} arxiv={p.get("arxiv_id","-")} score={overall}')
