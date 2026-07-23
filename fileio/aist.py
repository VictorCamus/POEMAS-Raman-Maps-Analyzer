import struct
import numpy as np
from classes import ChannelData
from process.converter import nm_to_raman, nm_to_eV

# =========================================================
# BUFFER READER (equivalent a punters en C)
# =========================================================

class BufferReader:
    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0

    def remaining(self):
        return len(self.data) - self.pos

# =========================================================
# LECTORS QT
# =========================================================

def read_qt_int(r):
    if r.remaining() < 4:
        raise ValueError
    v = struct.unpack(">i", r.data[r.pos:r.pos+4])[0]
    r.pos += 4
    return v

def read_qt_double(r):
    if r.remaining() < 8:
        raise ValueError
    v = struct.unpack(">d", r.data[r.pos:r.pos+8])[0]
    r.pos += 8
    return v

def read_qt_bool(r):
    if r.remaining() < 1:
        raise ValueError
    v = r.data[r.pos] != 0
    r.pos += 1
    return v

def read_qt_byte(r):
    if r.remaining() < 1:
        raise ValueError
    v = r.data[r.pos]
    r.pos += 1
    return v

def read_qt_string(r):
    length = read_qt_int(r)

    if length == 0:
        return ""

    # if r.remaining() < length:
    #     raise ValueError

    raw = r.data[r.pos:r.pos+length]
    r.pos += length

    return raw.decode("utf-16-be")

def read_qt_byte_array(r, dtype = "<f8", uncompressed = False):
    length = read_qt_int(r)
    if uncompressed: length = read_qt_int(r)

    if length == -1:
        return None

    if r.remaining() < length:
        raise ValueError

    value = np.frombuffer(r.data[r.pos:r.pos+length], dtype=dtype)
    r.pos += length

    return value

# =========================================================
# FUNCIONS AUXILIARS
# =========================================================

def read_aist_common(r):
    return {
        "id": read_qt_int(r),
        "name": read_qt_string(r),
        "description": read_qt_string(r),
        "index": read_qt_int(r),
    }

def read_aist_common_spectro(r):
    return {
        "name": read_qt_string(r),
        "description": read_qt_string(r),
        "index": read_qt_int(r),
    }

def extract_units(label):
    # Versió simplificada (sense Gwyddion)
    if "[" in label and "]" in label:
        return label.split("[")[1].split("]")[0]
    return label

# =========================================================
# RASTER
# =========================================================

def read_aist_raster(r):
    common = read_aist_common(r)

    xres = read_qt_int(r)
    yres = read_qt_int(r)

    left = read_qt_double(r)
    right = read_qt_double(r)
    bottom = read_qt_double(r)
    top = read_qt_double(r)

    xunits = read_qt_string(r)
    yunits = read_qt_string(r)
    zunits = read_qt_string(r)

    values = read_qt_byte_array(r)

    values = values.reshape((yres, xres))
    values = np.flipud(values)

    result = {
        "type": "raster",
        "common": common,
        "data": values,
        "xres": xres,
        "yres": yres,
        "extent": (left, right, bottom, top),
        "units": {
            "x": extract_units(xunits),
            "y": extract_units(yunits),
            "z": extract_units(zunits),
        }
    }

    # MASK (opcional)
    try:
        mask_data = read_qt_byte_array(r)
        if mask_data and len(mask_data) == xres * yres:
            mask = np.frombuffer(mask_data, dtype=np.uint8)
            mask = mask.reshape((yres, xres))
            mask = np.flipud(mask)
            result["mask"] = mask
    except:
        pass

    # view data (ignorat)
    try:
        read_qt_byte_array(r)
    except:
        pass

    return result

# =========================================================
# CURVE
# =========================================================

def read_aist_curve(r):
    common = read_aist_common(r)

    res = read_qt_int(r)

    arr = read_qt_byte_array(r)
    _ = read_qt_byte_array(r)  # view data ignorat

    xunits = read_qt_string(r)
    yunits = read_qt_string(r)

    x = arr[:res]
    y = arr[res:]

    return {
        "type": "curve",
        "common": common,
        "x": x,
        "y": y,
        "units": {
            "x": extract_units(xunits),
            "y": extract_units(yunits),
        }
    }

# =========================================================
# CURVE
# =========================================================

def read_aist_spectro(r):
    spectra = read_qt_byte_array(r, dtype="<f4", uncompressed=True)
    common_spec = read_aist_common_spectro(r)

    _ = read_qt_int(r)
    _ = read_qt_int(r)

    laser = read_qt_double(r)
    _ = read_qt_double(r)
    _ = read_qt_double(r)
    _ = read_qt_int(r)
    _ = read_qt_int(r)

    nchan = read_qt_int(r)
    q_vec = read_qt_byte_array(r, dtype="<f4")

    common = read_aist_common(r)

    xres = read_qt_int(r)
    yres = read_qt_int(r)

    left = read_qt_double(r)
    right = read_qt_double(r)

    bottom = read_qt_double(r)
    top = read_qt_double(r)

    xunits = read_qt_string(r)
    yunits = read_qt_string(r)

    _ = read_qt_int(r)
    nspec = read_qt_int(r)

    spectra = spectra.reshape(nspec, nchan)

    return {
        "type": "spectro",
        "common": common_spec,
        "laser": laser,
        "spectra": spectra,
        "xdata": q_vec,
        "xres": xres,
        "yres": yres,
        "extent": (left, right, bottom, top),
        "units": {
            "x": extract_units(xunits),
            "y": extract_units(yunits),
            "z": "nm",
        }
    }

# =========================================================
# DATA NODE
# =========================================================

READERS = {
    "raster": read_aist_raster,
    "curve": read_aist_curve,
    "spectro": read_aist_spectro,
}

def read_aist_data(r):
    type_ = read_qt_string(r)
    
    if type_ == 'spectro': return read_aist_spectro(r), type_
    length = read_qt_int(r)

    if r.remaining() < length:
        raise ValueError

    sub = BufferReader(r.data[r.pos:r.pos+length])

    r.pos += length
    reader = READERS.get(type_)

    if reader is None:
        return None

    return reader(sub), type_

# =========================================================
# TREE RECURSIU
# =========================================================

def read_aist_tree(r, results):
    is_data = read_qt_bool(r)
    type_ = None
    if is_data:
        data, type_ = read_aist_data(r)
        if data: results.append(data)

    if type_ == 'spectro': return results
    name = read_qt_string(r)     
    nchildren = read_qt_int(r)
    for _ in range(nchildren):
        read_aist_tree(r, results)

# =========================================================
# FUNCIÓ PRINCIPAL
# =========================================================

def load_aist(filename):
    with open(filename, "rb") as f:
        data = f.read()

    reader = BufferReader(data)
    results = []

    read_aist_tree(reader, results)

    if not results:
        raise ValueError("No data found")

    return results

def load(file_list, fileclass):
    file = file_list[0]
    maps = {'Height(Sen)': 'Height', 'Mag': 'Mag', 'Phase': 'Phase', 'CPD[2]': 'CPD'}
    data = load_aist(file)

    channels = {}
    N = None
    mida = None

    for d in data:
        if N is None:
            N = (d['xres'], d['yres'])
            extent = d['extent']
            mida = (extent[1]-extent[0], extent[3]-extent[2])

        match d["type"]:
            case "raster":
                name = d['common']['name']
                laser = None
                if name == 'CPD': continue
                if name.endswith('[2]') and name != 'CPD[2]': continue

                tipus = maps[name]
                channels[tipus] = ChannelData(name = tipus, Z = np.array(d['data'][::-1]), units = d['units']['z'], lims = None)

            case "spectro":
                xdata_nm = d['xdata']
                xdata = {'nm': xdata_nm,
                         'eV': nm_to_eV(xdata_nm),
                         '1/cm': nm_to_raman(xdata_nm, d['laser'])}

                spectra = d['spectra'].reshape(N[1], N[0], d['spectra'].shape[1]).copy()
                laser = d['laser']
                channels['Spectra'] = ChannelData(name = 'Spectra', units = d['units']['z'], lims = None, xdata = xdata, spectra = spectra)

    data = {'channel': channels, 'N': N, '_midaBase': mida, 'laser': laser}

    return fileclass(**data)