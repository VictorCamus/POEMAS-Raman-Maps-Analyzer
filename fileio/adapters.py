from . import aist, h5, xyz, wsxm, txtraman

FORMAT_MAP = {
    '.aist': aist,
    '.h5': h5,
    '.xyz': xyz,
    '.wsxm': wsxm,
    '.txt': txtraman
}

def open_file(file_list, format):
    module = FORMAT_MAP[format]
    return module.load(file_list)