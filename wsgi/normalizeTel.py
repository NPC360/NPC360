def normalizeTel(tel):
    nTel = re.sub(r'[^a-zA-Z0-9\+]','', tel)
    return nTel
