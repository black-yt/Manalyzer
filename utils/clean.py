def clean_dict(d: dict, len_th=100):
    new_d = {}
    for k, v in d.items():
        k_str = k if isinstance(k, str) else str(k)
        if isinstance(v, str):
            new_d[k_str] = [v]
        elif isinstance(v, list):
            new_d[k_str] = []
            for x in v:
                if isinstance(x, str):
                    new_d[k_str].append(x)
                else:
                    new_d[k_str].append(str(x))
        elif isinstance(v, dict):
            new_d[k_str] = []
            for kk, vv in v.items():
                new_d[k_str].append(str(kk)+'\n'+str(vv))
        else:
            new_d[k_str] = [str(v)]

    new_d_2 = {}
    for k, v in new_d.items():
        if len(v) > 0:
            filtered_v = []
            for t in v:
                if len(t) > len_th or '.jpg' in t:
                    filtered_v.append(t)
            new_d_2[k] = filtered_v
    
    new_d_3 = {}
    for k, v in new_d_2.items():
        if len(k.replace(' ', ''))/len(k.split(' ')) <= 2:
            k = k.replace(' ', '')
        new_d_3[k] = v

    return new_d_3