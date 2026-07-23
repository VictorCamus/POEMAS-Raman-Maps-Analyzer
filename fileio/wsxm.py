from classes import ChannelData

MAGIC1a = b"WSxM file copyright Nanotec Electronica"
MAGIC1b = b"WSxM file copyright WSxM solutions"
MAGIC2 = b"SxM Image file"
HEADER_END = b"[Header end]\r\n"
SIZE_HEADER = b"Image header size:"

def read_newline(data, idx):
    if data[idx:idx+1] == b"\n":
        return idx + 1
    elif data[idx:idx+2] == b"\r\n":
        return idx + 2
    return None

def check_magic(data):
    if data.startswith(MAGIC1a):
        idx = len(MAGIC1a)
    elif data.startswith(MAGIC1b):
        idx = len(MAGIC1b)
    else:
        return None

    idx = read_newline(data, idx)
    if idx is None:
        return None

    if not data[idx:].startswith(MAGIC2):
        return None

    idx += len(MAGIC2)
    idx = read_newline(data, idx)

    return idx

def find_header_end(data):
    pos = data.find(HEADER_END)
    if pos == -1:
        raise ValueError("No s'ha trobat [Header end]")
    return pos + len(HEADER_END)

def parse_header(header_bytes):
    text = header_bytes.decode("latin-1")
    lines = text.splitlines()

    meta = {}
    section = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        if line.startswith("[") and line.endswith("]"):
            section = line.strip("[]")
            continue

        if ":" in line:
            key, value = line.split(":", 1)
            key = key.strip()
            value = value.strip()
            full_key = f"{section}::{key}" if section else key
            meta[full_key] = value

    return meta

def get_lateral_size(meta, Nx, Ny):
    def parse_value_unit(s):
        try:
            parts = s.split()
            value = float(parts[0])
            unit = parts[1] if len(parts) > 1 else "m"

            # conversió a µm (com al teu xyz)
            factors = {
                "m": 1e6,
                "mm": 1e3,
                "um": 1,
                "µm": 1,
                "nm": 1e-3,
            }

            return value * factors.get(unit, 1), unit
        except:
            return None, None

    x_amp = meta.get("Control::X Amplitude")
    y_amp = meta.get("Control::Y Amplitude")

    if x_amp:
        midaX, _ = parse_value_unit(x_amp)
    else:
        midaX = Nx  # fallback

    if y_amp:
        midaY, _ = parse_value_unit(y_amp)
    else:
        midaY = Ny  # fallback

    return round(midaX, 3), round(midaY, 3)

def read_data_field(buffer, xres, yres, dtype):
    if dtype == "double":
        data = np.frombuffer(buffer, dtype=np.float64).copy()
    elif dtype == "float":
        data = np.frombuffer(buffer, dtype=np.float32).copy()
    else:
        raise ValueError(f"Tipus desconegut: {dtype}")

    data = data.reshape((yres, xres))
    data = np.flipud(np.fliplr(data))

    return data

def load_wsxm(filename):
    with open(filename, "rb") as f:
        data = f.read()

    idx = check_magic(data)
    if idx is None:
        raise ValueError("No és un fitxer WSxM vàlid")

    header_end = find_header_end(data)
    header = data[:header_end]

    meta = parse_header(header)

    # Extreure resolució
    try:
        xres = int(meta["General Info::Number of columns"])
        yres = int(meta["General Info::Number of rows"])
    except KeyError:
        raise ValueError("Falten dimensions")

    dtype = meta.get("General Info::Image Data Type", "double")

    binary_data = data[header_end:]

    image = read_data_field(binary_data, xres, yres, dtype)

    return image, meta

def load(file_list, fileclass):
    type_map = {'.top': 'AFM', '.Auxfeed': 'CPD', '.ch15': 'MAG', '.ch16': 'PHASE'}
    channels = {}

    for file in file_list:
        name = type_map[file.suffix]

        Z, meta = load_wsxm(file)

        Ny, Nx = Z.shape
        mida = get_lateral_size(meta, Nx, Ny)
        N = Nx, Ny

        channels[name] = ChannelData(name=name, Z=Z)

    data = {'channel': channels, 'N': N, '_midaBase': mida}
    return fileclass(**data)