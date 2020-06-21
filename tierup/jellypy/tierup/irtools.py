"""Utilities for handling interpretation request data."""
import json
import logging
import pathlib
import re
import requests

import jellypy.pyCIPAPI.interpretation_requests as irs
import jellypy.tierup.panelapp as pa

from collections import Counter
from datetime import datetime
from jellypy.pyCIPAPI.auth import AuthenticatedCIPAPISession
from protocols.reports_6_0_1 import InterpretedGenome


logger = logging.getLogger(__name__)


class IRJValidator:
    """Validate interpretation request json data for TierUp reanalysis.

    Args:
        None
    """

    def __init__(self):
        pass

    def validate(self, irjson: dict):
        """Call methods to validate the interpretation request data for TierUp reanalysis.

        Args:
            irjson: Interpretation request data in JSON format
        Raises:
            IOError: A validation function returns False
            KeyError: Expected keys are missing from the JSON object
        """
        try:
            is_v6 = self.is_v6(irjson)
            is_sent = self.is_sent(irjson)
            is_unsolved = self.is_unsolved(irjson)
        except KeyError:
            # An expected key is missing from the JSON.
            raise ValueError(
                f"Invalid interpretation request JSON: An expected key is missing. "
                "Is this a v6 JSON?"
            )

        if is_v6 and is_sent and is_unsolved:
            pass
        else:
            raise IOError(
                f"Invalid interpretation request JSON: "
                f"is_v6:{is_v6}, is_sent:{is_sent}, is_unsolved:{is_unsolved}"
            )

    @staticmethod
    def is_v6(irjson: dict) -> bool:
        """Returns true if the interpreted genome of an irjson is GeL v6 model.
        Even when using the report_v6 API flag, older interpretation requests won't match this schema.

        Args:
            irjson: Interpretation request data in json format.
        """
        return InterpretedGenome.validate(irjson["interpreted_genome"][0]["interpreted_genome_data"])

    @staticmethod
    def is_sent(irjson: dict) -> bool:
        """Check if the interpretation request submitted to the interpretation portal by GeL.
        This happens once all QC checks are passed and a decision support service has processed data.

        Args:
            irjson: Interpretation request data in json format.
        """
        return "sent_to_gmcs" in [item["status"] for item in irjson["status"]]

    @staticmethod
    def is_unsolved(irjson: dict) -> bool:
        """Returns True if no reports have been issued where the case has been solved.

        Args:
            irjson: Interpretation request data in json format.
        """
        # If a report has not been issued, the clinical_report field will be an empty list. Return True.
        if not irjson["clinical_report"]:
            return True

        reports = irjson["clinical_report"]
        reports_with_questionnaire = [
            report for report in reports if report["exit_questionnaire"] is not None
        ]
        reports_solved = [
            report
            for report in reports_with_questionnaire
            if report["exit_questionnaire"]["exit_questionnaire_data"][
                "familyLevelQuestions"
            ]["caseSolvedFamily"]
            == "yes"
        ]
        if any(reports_solved):
            return False
        else:
            return True


class IRJson:
    """Parses interpretation request json data for TierUp

    Args:
        irjson: An interpretation request json object
        validator: An IRJValidator instance. No validation is performed if this is None.
    Attributes:
        json(dict): Interpretation request json data passed as the `irjson` argument
        irid(str): The interpretation request id and version e.g. 1243-1
        proband_id(str): The proband GeL ID
        tiering(dict): The GeL interpreted genome with tiering pipeline data
        panels(dict): name:jellypy.tierup.panelapp.GeLPanel objects for each panel in the
            interpretation request metadata
        updated_panels(list): A list of panel ids added to self.panels using `self.update_panel()`.
    Methods:
        update_panel: Assign a more recent PanelApp ID to a panel in the interpretation request
    """

    def __init__(self, irjson: dict, validator=IRJValidator):
        if validator:
            validator().validate(irjson)
        self.json = irjson
        self.tiering = self._get_tiering()
        self.panels = self._get_panels()
        self.updated_panels = []

    def __str__(self):
        return f"{self.irid}"

    def _get_tiering(self):
        """Return the latest GeL tiering interpreted genome from the interpretation request json."""
        tiering_list = list(
            filter(
                lambda x: x["interpreted_genome_data"]["interpretationService"]
                == "genomics_england_tiering",
                self.json["interpreted_genome"],
            )
        )
        latest_tiering = max(
            tiering_list, key=lambda x: datetime.strptime(x['created_at'], "%Y-%m-%dT%H:%M:%S.%fZ")
        )
        return latest_tiering

    def _get_panels(self):
        """Get GeL panel data from PanelApp. Returns a dictionary mapping panel names to GeLPanel
        objects from jellypy.tierup.panelapp."""
        _panels = {}
        data = self.json["interpretation_request_data"]["json_request"]["pedigree"][
            "analysisPanels"
        ]
        for item in data:
            try:
                panel = pa.GeLPanel(item["panelName"])
                _panels[panel.name] = panel
            except requests.HTTPError:
                logger.warning(f"Warning. No PanelApp API reponse for {item}")
        return _panels

    def update_panel(self, panel_name, panel_id):
        """Add or update a panel name in self.panels using a GeL panel app ID."""
        new_panel = pa.GeLPanel(panel_id)
        self.panels[panel_name] = new_panel
        self.updated_panels.append(f"{panel_name}, {panel_id}")

    @property
    def irid(self):
        irid_full = self.tiering["interpreted_genome_data"]["interpretationRequestId"]
        irid_digits = re.search(r'\d+-\d+', irid_full).group(0)
        return irid_digits

    @property
    def proband_id(self):
        participants = self.json['interpretation_request_data']['json_request']['pedigree']['members']
        proband = next( patient for patient in participants if patient['isProband'] == True )
        return proband['participantId']

class IRJIO:
    """Utilities for reading, writing and downloading interpretation request json data."""

    def __init__(self):
        pass

    @classmethod
    def get(
        cls: object, irid: int, irversion: int, session: AuthenticatedCIPAPISession
    ) -> IRJson:
        """Get an interpretation request json from the CPIAPI using jellypy.pyCIPAPI library

        Args:
            irid: Interpretation request id
            irversion: Interpretation request version
            session: An authenticated CIPAPI session (pyCIPAPI)
        Returns:
            An IRJson object
        """
        json_response = irs.get_interpretation_request_json(
            irid, irversion, reports_v6=True, session=session
        )
        return IRJson(json_response)

    @classmethod
    def read(cls, filepath: str) -> IRJson:
        """Read an interpretation request json from a file.

        Args:
            filepath: Path to interpretation request json file
        Returns:
            An IRJson object"""
        with open(filepath, "r") as f:
            return IRJson(json.load(f))

    @classmethod
    def save(cls, irjson: IRJson, filename: str = None, outdir: str = ""):
        """Save IRJson to disk"""
        _fn = filename or irjson.irid + ".json"
        outpath = pathlib.Path(outdir, _fn)
        with open(outpath, "w") as f:
            json.dump(irjson.json, f)
