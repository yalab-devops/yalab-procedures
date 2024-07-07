import json
from pathlib import Path

from nipype.interfaces import io as nio

DEFAULT_OUTPUT_QUERY = Path(__file__).parent / "default_bids_query.json"


class YALabBidsQuery(nio.BIDSDataGrabber):
    """
    A simple wrapper around the BIDSDataGrabber interface that sets the output query to the default query.
    """

    def __init__(self, *args, **kwargs):
        super(YALabBidsQuery, self).__init__(*args, **kwargs)
        self._update_output_query()

    def _update_output_query(self):
        """
        Update the output query with the default query.
        """
        with open(DEFAULT_OUTPUT_QUERY, "r") as f:
            output_query = json.load(f)
        self.inputs.output_query.update(output_query)
