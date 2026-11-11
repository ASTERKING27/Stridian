import sys,json;sys.path.insert(0,'backend')
import sports_config as s
# sample athlete scores 0-100 per sport, in metric order (first five non-match metrics)
SCORES={'Football':None,'Basketball':[62,58,84,80,55],'Volleyball':[72,80,85,48,60],'Cricket':[60,52,70,88,58],
 'Badminton':[82,85,60,70,55],'Tennis':[55,50,62,86,82],'Kho-Kho':[88,86,58,60,40]}
FB={'sprint30m':4.38,'cmj':36,'agilityTtest':9.62,'yoyoLevel':17.4,'heightCm':172}
out={}
for sp,v in s.SPORTS.items():
    ms=[m for m in v['metrics'] if 'uncalibrated' not in m['label'] and not m['key'].startswith('match') and not m['key'].startswith('card_')][:5]
    mets=[]
    for i,m in enumerate(ms):
        if sp=='Football':
            val=FB[m['key']]; sc=round(max(0,min(100,(val-m['poor'])/(m['elite']-m['poor'])*100)))
        else:
            sc=SCORES[sp][i]; val=m['poor']+(m['elite']-m['poor'])*sc/100
        unit={'sec':'s'}.get(m['unit'],m['unit'])
        fmt=f"{val:.2f}" if m['unit'] in('sec','m') else f"{val:.1f}" if m['unit']=='level' else f"{val:.0f}"
        lab=m['label'].split(' (')[0].replace(' Level','').replace(' Test','')
        mets.append({'label':lab,'val':fmt+' '+unit,'score':sc})
    poss=[]
    for pn,pv in v['positions'].items():
        w=[pv['weights'].get(m['key'],0) for m in ms]; t=sum(w) or 1
        w=[x/t for x in w]
        wr=[round(x*100) for x in w]
        fit=round(sum(w[i]*mets[i]['score'] for i in range(len(mets))))
        poss.append({'name':pn,'fit':fit,'w':wr,'blurb':pv.get('blurb','')})
    out[sp]={'metrics':mets,'positions':poss}
    print(sp,[m['label'] for m in mets],sorted([(p['fit'],p['name']) for p in poss],reverse=True)[:3],file=sys.stderr)
print(json.dumps(out))
