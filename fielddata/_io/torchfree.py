# Copied verbatim from battery-field-data/reproductions/_tools/torchfree.py.
"""Read torch.save() pickles without PyTorch. Handles the legacy tar-less format
(magic, protocol, sysinfo, pickle, storage keys, raw storages), the zip format
(archive/data.pkl + archive/data/<key>), and plain pickles whose storages are
embedded via torch.storage._load_from_bytes. Returns numpy arrays.
Imported 2026-09-09. Used for cao (QAS/GIS/DTI vin_*.pkl) and evbattery/zhang snippets."""
import pickle, io, struct, zipfile, collections
import numpy as np

DT = {'FloatStorage': np.float32, 'DoubleStorage': np.float64, 'LongStorage': np.int64,
      'IntStorage': np.int32, 'HalfStorage': np.float16, 'ByteStorage': np.uint8, 'BoolStorage': np.bool_}

class _ST:
    def __init__(self, name): self.name = name

class _Lazy:
    def __init__(self, key, off, size, stride): self.key, self.off, self.size, self.stride = key, off, tuple(size), tuple(stride)

def _rebuild(storage, offset, size, stride, *a):
    if isinstance(storage, np.ndarray):
        return np.lib.stride_tricks.as_strided(storage[offset:], shape=tuple(size),
                                               strides=tuple(s * storage.itemsize for s in stride)).copy()
    return _Lazy(storage, offset, size, stride)

def _materialize(o, data):
    if isinstance(o, _Lazy):
        s = data[o.key]
        return np.lib.stride_tricks.as_strided(s[o.off:], shape=o.size, strides=tuple(x * s.itemsize for x in o.stride)).copy()
    if isinstance(o, list): return [_materialize(x, data) for x in o]
    if isinstance(o, tuple): return tuple(_materialize(x, data) for x in o)
    if isinstance(o, dict): return type(o)((k, _materialize(v, data)) for k, v in o.items())
    return o

def _find_class(mod, name, fallback):
    if mod == 'torch._utils' and name == '_rebuild_tensor_v2': return _rebuild
    if mod == 'torch' and name in DT: return _ST(name)
    if mod == 'torch' and name == 'Size': return tuple
    if mod == 'collections' and name == 'OrderedDict': return collections.OrderedDict
    if mod == 'torch.storage' and name == '_load_from_bytes': return _load_from_bytes
    return fallback(mod, name)

def _load_from_bytes(b):
    """Embedded legacy storage blob (used by older pickles)."""
    f = io.BytesIO(b); pickle.load(f); pickle.load(f); pickle.load(f)
    class U(pickle.Unpickler):
        def find_class(self, mod, name): return _find_class(mod, name, super().find_class)
        def persistent_load(self, pid): return pid
    obj = U(f).load(); pickle.load(f)
    numel = struct.unpack('<q', f.read(8))[0]; dt = DT[obj[1].name]
    return np.frombuffer(f.read(numel * np.dtype(dt).itemsize), dtype=dt)

def load_legacy(raw):
    f = io.BytesIO(raw); pickle.load(f); pickle.load(f); pickle.load(f)
    storages = {}
    class LU(pickle.Unpickler):
        def find_class(self, mod, name): return _find_class(mod, name, super().find_class)
        def persistent_load(self, pid):
            typ, st, key, loc, numel = pid[:5]; storages[key] = DT[st.name]; return key
    obj = LU(f).load(); keys = pickle.load(f); data = {}
    for key in keys:
        n = struct.unpack('<q', f.read(8))[0]; dt = storages[key]
        data[key] = np.frombuffer(f.read(n * np.dtype(dt).itemsize), dtype=dt)
    return _materialize(obj, data)

def load_zip(raw):
    z = zipfile.ZipFile(io.BytesIO(raw)); names = z.namelist()
    pk = next(n for n in names if n.endswith('data.pkl')); root = pk[:-len('data.pkl')]
    class ZU(pickle.Unpickler):
        def find_class(self, mod, name): return _find_class(mod, name, super().find_class)
        def persistent_load(self, pid):
            typ, st, key, loc, numel = pid[:5]
            return np.frombuffer(z.read(root + 'data/' + str(key)), dtype=DT[st.name])
    return ZU(io.BytesIO(z.read(pk))).load()

def load_plain(raw):
    class TU(pickle.Unpickler):
        def find_class(self, mod, name): return _find_class(mod, name, super().find_class)
    return TU(io.BytesIO(raw)).load()

def load(raw):
    """Try zip, then legacy, then plain pickle."""
    if raw[:2] == b'PK': return load_zip(raw)
    try: return load_legacy(raw)
    except Exception: return load_plain(raw)