"""Raw-word replay diagnostic. Not a simulator or a coherent-error estimator."""
from collections import Counter
P=2**256-2**32-977
F=2**32+977
M=2**256-1
INV2=(P+1)//2

def walk(d, rounds=736, margin=20):
    u,v=P,d
    tape=[]
    bad=None
    convergence=None
    for k in range(rounds):
        w=min(259,max(8,(256+margin-17*k//100 if k<40 else
                         250+margin-33*(k-40)//100 if k<304 else
                         163+margin-40*(k-304)//100)))
        fits=lambda x: -(1<<(w-1)) <= x < 1<<(w-1)
        if not fits(u) or not fits(v):
            bad=bad or (k,'input_width')
        if k==0:
            tape.append(d&1)
            v=d//2-P+((d>>1)&1)*P+(d&1)*((P+1)//2)
        else:
            s,t=(u,v) if k%2==0 else (v,u)
            sign=((s>>1)^(t>>1))&1
            total=t+(-s if sign else s)
            assert total%2==0
            if not fits(total): bad=bad or (k,'sum_width')
            if k%2==0: v=total//2
            else: u=total//2
            tape.append(sign)
        if convergence is None and max(abs(u),abs(v))==1:
            convergence=k+1
    return tape,u,v,bad,convergence

def low_add(x,c,w):
    mask=(1<<w)-1
    return (x&~mask)|((x+c)&mask)

def chunks(source,target,compare,events):
    cin=0
    out=0
    lo=0
    for width in (86,85,85):
        mask=(1<<width)-1
        a=(source>>lo)&mask
        t=(target>>lo)&mask
        total=a+t+cin
        z=total&mask
        co=total>>width
        if lo+width<256:
            pred=int((z>>(width-compare)) < (a>>(width-compare)))
            if pred!=co: events['chunk_predicate']+=1
            if int(z<a)!=co: events['chunk_equality']+=1
            if pred!=int(z<a): events['chunk_prefix']+=1
        out|=z<<lo
        lo+=width
        cin=co
    return out,cin

def ordinary(s,t,sign,inverse,fold,compare,flag,events):
    before=t
    d=t>>255 if inverse else 0
    raw=(2*t)&M if inverse else t
    raw ^= M if sign else 0
    raw,o=chunks(s,raw,compare,events)
    parity=raw&1
    if inverse:
        correction=(o-d if sign else o+d)*F
    else:
        minus=(1-o)*(1-sign)*parity
        plus2=o*sign*parity
        plus=minus^sign^parity
        correction=(plus+2*plus2-minus)*F
    folded=low_add(raw,correction,fold)
    if folded != (raw+correction)&M: events['fold_width']+=1
    pred=int((folded>>(256-flag)) < (s>>(256-flag)))
    if pred!=o: events['flag_predicate']+=1
    if int(folded<s)!=o: events['flag_fullwidth_defect']+=1
    if pred!=int(folded<s): events['flag_prefix']+=1
    result=folded^(M if sign else 0)
    if not inverse:
        result=(result>>1)|((parity^o^sign)<<255)
    expected=((2*before if inverse else before)+(-s if sign else s))%P
    if not inverse: expected=expected*INV2%P
    if result%P!=expected: events['ordinary_value']+=1
    return result

def replay(d,c,inverse=False,guarded=True,trace=None):
    rounds,margin,fold,compare,flag,endpoint=(736,20,72,40,48,71) if guarded else (704,4,56,26,28,55)
    tape,u,v,bad,convergence=walk(d,rounds,margin)
    events=Counter()
    if bad: events['value_width']+=1
    if convergence is None: events['round_budget']+=1
    def negate(x,sgn):
        if not sgn: return x
        out=low_add(x^M,-(F-1),min(256,32+endpoint+2))
        if out%P!=(-x)%P: events['endpoint_width']+=1
        return out
    if inverse: x,y=negate(c,u<0),negate(c,v<0)
    else: x,y=0,c
    first_value=None
    indices=reversed(range(rounds)) if inverse else range(rounds)
    for k in indices:
        s,t=(x,y) if k%2==0 else (y,x)
        target_before=t
        before_events=events['ordinary_value']
        if k>=2:
            t=ordinary(s,t,tape[k]^int(inverse),inverse,fold,compare,flag,events)
        elif inverse:
            old=t
            t=low_add((2*t)&M,(t>>255)*F,min(256,32+endpoint+2))
            if t%P!=(2*old)%P: events['endpoint_width']+=1
            if k==1:
                t=low_add(t,tape[k]*(F-1),66)^(M if tape[k] else 0)^s
        else:
            if k==1:
                t=low_add(s^(M if tape[k] else 0),-tape[k]*(F-1),66)
            old=t
            parity=t&1
            t=low_add(t,-parity*F,min(256,32+endpoint+2))
            t=(t>>1)|(parity<<255)
            if t%P!=old*INV2%P: events['endpoint_width']+=1
        if k%2==0: y=t
        else: x=t
        if trace is not None: trace.append((k,x,y))
        if first_value is None and events['ordinary_value']>before_events:
            first_value={'round':k,'source':hex(s),'target_before':hex(target_before),'result':hex(t)}
    if not inverse: x,y=negate(x,u<0),negate(y,v<0)
    expected=c*(d if inverse else pow(d,-1,P))%P
    return {'output':hex(y),'expected':hex(expected),'classical':y!=expected,
            'convergence':convergence,'first_width':bad,'events':dict(events),
            'coefficient':hex(x if inverse else x^y),'first_value':first_value}
