class SelectorMixin:

    def _set_selector(self, key, items, current=None):
        combo = self.widgets[key].widget

        if not items:
            combo.config(values=[])
            combo.options = {}
            combo.set('')
            return None

        keys = [item[0] for item in items]
        labels = [item[1] for item in items]

        combo.config(values=labels)
        combo.options = dict(zip(labels, keys))

        if current not in keys:
            current = keys[0]

        combo.set(labels[keys.index(current)])

        return current

    def _clear_selector(self, key):
        combo = self.widgets[key].widget

        combo.config(values=[])
        combo.options = {}
        combo.set('')

class FileChannelMixin(SelectorMixin):
    
    def __init__(self, gestor):
        self._file = gestor.current_file
        self._channel = self._file.current_channel

        self.files = gestor.files

        self.file_key = self.file.name
        self.channel_key = self.channel.name

        self._file_ref = None

        self.notebook = gestor.notebook

    @property
    def file(self):
        return self._file
    
    @file.setter
    def file(self, value):
        if value != "Tots els mapes": self._file = self.files[value]
        self.file_key = value
        self.update_channels()

    @property
    def file_ref(self):
        return self._file_ref
    
    @file_ref.setter
    def file_ref(self, value):
        self._file_ref = self.files[value]
        self.update_channels()
        
    @property
    def channel(self):
        return self._channel
    
    @channel.setter
    def channel(self, value):
        if value is None: return
        if value in self.file.channel: self._channel = self.file.channel[value]
        self.channel_key = value

        if self.file_key == "Tots els mapes": return
        
        if self.update: self.file.view.selector.select(self.channel.tab)

    def files_list(self):
        if self.file_key == "Tots els mapes":
            files = list(self.files.values())
        else:
            files = [self.file]
            if self.file_ref is not None and self.file_ref is not self.file: files.append(self.file_ref)
            if self.update: self.notebook.select(self.file.view.tab)

        return files
    
    def compare_files(self):
        list_files = ["Tots els mapes"] + list(self.files.keys())
        self._file_ref = self.files[list_files[1]]
        
        channels = list(self.file_ref.channel.keys() & self.file.channel.keys())
        
        if self.channel.name in channels: initCh = self.channel.name
        else: initCh = channels[0]

        return list_files, channels, initCh
    
    def update_channels(self):
        if not hasattr(self, 'file') or not hasattr(self, 'widgets'): return
        if not "channel" in self.widgets: return

        files = self.files_list()
        channels = list(files[0].channel)

        if self.intersect:
            common = set.intersection(*(set(f.channel) for f in files))
            channels = [ch for ch in channels if ch in common]
        else:
            for f in files[1:]:
                for ch in f.channel:
                    if ch not in channels:
                        channels.append(ch)

        self.update_channel_combobox(channels)

    def update_files(self, files):
        self._set_selector('file', [(file, file) for file in files], self.file_key)

    def update_channel_combobox(self, channels):
        current = self._set_selector('channel', [(channel, channel) for channel in channels], self.channel_key)

        if current is not None: self.channel = current

class FitPeakParameterMixin(SelectorMixin):

    def __init__(self):
        self._fit = None
        self._peak = None
        self._parameter = None

        self.fit_key = None
        self.peak_key = None
        self.parameter_key = None

        self.include_rawdata = False
        self.include_r2 = False
        
    @property
    def fit(self):
        return self._fit

    @fit.setter
    def fit(self, value):
        fits = self.channel.spectra.fits

        if value == 'rawdata' and self.include_rawdata:
            self.fit_key = 'rawdata'
            self._fit = None
            self.peak = None
            self.parameter = None
            self._on_rawdata_selected()
            return

        if value not in fits:
            return

        self._fit = fits[value]
        self.fit_key = value

        # Seleccionem el primer pic
        if self.fit.peaks:
            self._peak = next(iter(self.fit.peaks.values()))
            self.peak_key = self._peak.ref

            if self.parameter_key in self.peak.parameter_names:
                self._parameter = self.peak.get_parameter(self.parameter_key)
            else:
                self.parameter_key, self._parameter = next(
                    iter(self.peak.params.items())
                )

        self._on_fit_selected()
        self.update_peaks()

    @property
    def peak(self):
        return self._peak

    @peak.setter
    def peak(self, value):
        if value is None:
            self._clear_selector('peak')
            self._peak = None
            self.peak_key = None

            self.parameter = None
            return

        if value == 'r2' and self.include_r2:
            self._peak = None
            self.peak_key = 'r2'
            self.parameter = None

            self._on_r2_selected()
            return

        if value not in self.fit.peaks:
            return

        self._peak = self.fit.peaks[value]
        self.peak_key = value

        # Conservem el paràmetre si existeix en el nou pic
        if self.parameter_key in self.peak.parameter_names:
            self._parameter = self.peak.get_parameter(self.parameter_key)
        else:
            self.parameter_key, self._parameter = next(
                iter(self.peak.params.items())
            )

        self._on_peak_selected()
        self.update_params()

    @property
    def parameter(self):
        return self._parameter

    @parameter.setter
    def parameter(self, value):
        if value is None:
            self._clear_selector('parameter')
            self._parameter = None
            self.parameter_key = None
            return

        if self.peak is None or value not in self.peak.parameter_names:
            return

        self._parameter = self.peak.get_parameter(value)
        self.parameter_key = value

        self._on_parameter_selected()

    def update_fits(self):
        fits = list(self.channel.spectra.fits)
        if self.include_rawdata: fits.insert(0, 'rawdata')

        current = self._set_selector('fit', [(fit, fit) for fit in fits], self.fit_key)
        if current is not None: self.fit = current

    def update_peaks(self):
        if self.fit is None or not self.fit.peaks:
            self._clear_selector('peak')
            return

        items = [(ref, peak.name) for ref, peak in self.fit.peaks.items()]
        if self.include_r2: items.append(('r2', 'r2'))

        self.peak = self._set_selector('peak', items, self.peak_key)

    def update_params(self):
        if self.peak is None or not self.peak.params:
            self._clear_selector('parameter')
            return

        params = self.peak.parameter_names
        self.parameter = self._set_selector('parameter', [(param, param) for param in params], self.parameter_key)

    # Hooks
    def _on_fit_selected(self):
        pass

    def _on_rawdata_selected(self):
        pass

    def _on_peak_selected(self):
        pass

    def _on_r2_selected(self):
        pass

    def _on_parameter_selected(self):
        pass