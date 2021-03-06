from __future__ import absolute_import, division, print_function

from langkit.gdb.utils import dereference_fat_array_ptr


class AnalysisUnit(object):
    """
    Helper to deal with analysis units.
    """

    def __init__(self, value):
        self.value = value

    @property
    def filename(self):
        virtual_file = self.value['filename']
        vf_record = virtual_file['value'].dereference()
        v = dereference_fat_array_ptr(vf_record['full'])
        # TODO: replace the call to eval below with a call to the .string()
        # method. This does not work as of today because of a GDB bug: see
        # R219-011.
        return eval(str(v))
