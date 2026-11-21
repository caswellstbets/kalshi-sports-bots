"""Back-test for the Injury News model: when a rotation player sat unexpectedly (played the team's
previous game, not this one), how much had Kalshi's price moved by 3 hours before the start and by
the close, compared with what the Rotation player ratings say the absence was worth?

Caveat: "unexpectedly" is judged from box scores, so some of these absences were announced after
the 3-hour mark. That makes the 3-hour market look slower than it really was."""
import math, numpy as np
from collections import defaultdict
from statistics import NormalDist
from research.kalshi_join import load
from lab import boxscores, rapm, rotation
from lab.players import Tracker
N=NormalDist()


def run():
    games=[g for g in boxscores.load('.') if g['players'] and g['season_type'] in (2,3)]
    K={r['id']:r for r in load() if r['stype']==2 and r['t3'] and r['t0'] and r['t24']}
    by_day=defaultdict(list)
    for g in games: by_day[g['date'][:10]].append(g)
    tr=Tracker(); seen=[]; imp={}; rows=[]
    prm=rotation.params()
    for di,day in enumerate(sorted(by_day)):
        if len(seen)>=50 and di%2==0: imp=rapm.fit(seen,tr,now_index=di)
        for g in by_day[day]:
            if imp and g['id'] in K:
                # surprise absences: played the team's previous game, did not play this one
                res={}
                for t in (g['h'],g['a']):
                    last=tr.played_last.get(t) or set()
                    now={p['pid'] for p in g['players'] if p['team']==t and p.get('min',0)>0}
                    res[t]={p:1.0 for p in last-now if tr.exp_minutes(p)>=15}
                if res[g['h']] or res[g['a']]:
                    lagged={t:{p:1.0 for p in tr.roster(t) if p not in (tr.played_last.get(t) or set())} for t in (g['h'],g['a'])}
                    f0=rotation.features(tr,imp,g['h'],g['a'],g['date'],lagged[g['h']],lagged[g['a']])
                    f1=rotation.features(tr,imp,g['h'],g['a'],g['date'],{**lagged[g['h']],**res[g['h']]},{**lagged[g['a']],**res[g['a']]})
                    if f0 and f1:
                        dm=prm['margin']['strength']*(f1['strength_diff']-f0['strength_diff'])
                        k=K[g['id']]
                        pre=k['t24']['mid']
                        exp=N.cdf(N.inv_cdf(min(max(pre,.02),.98))+dm/14.6)
                        rows.append({'season':g['season'],'dm':dm,'pre':pre,'t3':k['t3']['mid'],'t0':k['t0']['mid'],'exp':exp,'y':1 if g['hs']>g['as'] else 0})
        for g in by_day[day]: tr.update(g); seen.append(g)

    rows = [r for r in rows if abs(r['dm']) >= 1.0]
    out = [f"{len(rows)} games where a rotation player sat unexpectedly and the ratings value it at 1+ points."]
    for key, name in (("t3", "3 hours before the start"), ("t0", "at the close")):
        gap = np.array([r['exp'] - r[key] for r in rows])
        resid = np.array([r['y'] - r[key] for r in rows])
        moved = np.array([r[key] - r['pre'] for r in rows])
        expm = np.array([r['exp'] - r['pre'] for r in rows])
        slope = np.polyfit(expm, moved, 1)[0]
        big = [(np.sign(g) * rr) for g, rr in zip(gap, resid) if abs(g) > 0.04]
        out.append(f"- {name}: Kalshi had moved {slope:.0%} of what the ratings say the absence was worth. Where the gap "
                   f"left was over 4 points ({len(big)} games), the side the news favoured beat the price by "
                   f"{100 * float(np.mean(big)) if big else 0:+.1f} points on average (noise at this sample size is about "
                   f"{100 * 0.5 / max(1, len(big)) ** 0.5:.0f} points).")
    return out


if __name__ == "__main__":
    print("\n".join(run()))
