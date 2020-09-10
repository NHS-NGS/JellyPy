"""
Takes directory of IR JSONs and checks if they are in v6 format, are
unsolved (i.e. have no clinical report and/or no exit questionaire) and
that it has been submitted to the interpretation portal.

This is analogous of functions in irtools.py from tierup branch 
(thanks Nana!)

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200907
"""

import json
import os
import shutil
import sys

from pathlib import Path
from protocols.reports_6_0_1 import InterpretedGenome


class validJSON():

    def __init__(self):
        pass

    def validate(self, irjson):
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
            is_rd = self.is_rd(irjson)
            is_38 = self.is_38(irjson)
        except KeyError:
            # An expected key is missing from the JSON.
            return False

        if is_v6 and is_sent and is_unsolved and is_rd and is_38:
            pass
        else:
            return False

    def is_v6(self, irjson):
        """Returns true if the interpreted genome of an irjson is GeL v6 model.
        Even when using the report_v6 API flag, older interpretation 
        requests won't match this schema.
        Args:
            irjson: Interpretation request data in json format.
        """
        return InterpretedGenome.validate(irjson["interpreted_genome"][0]["interpreted_genome_data"])

    def is_sent(self, irjson):
        """Check if the interpretation request submitted to the interpretation portal by GeL.
        This happens once all QC checks are passed and a decision support service has processed data.
        Args:
            irjson: Interpretation request data in json format.
        """
        return "sent_to_gmcs" in [item["status"] for item in irjson["status"]]

    def is_unsolved(self, irjson):
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
    
    def is_rd(self, irjson):
        """Returns true if JSON is a rare disease case. Required in case
        of mix of rare disease and cancer jsons
        """
        return "rare_disease" in irjson["program"]

    def is_38(self, irjson):
        """Returns true is assembly is build38, false if 37"""
        return "GRCh38" in irjson["assembly"]


    def main(self):
        """
        Main function to call validation of JSONs
        """

        dir = Path(sys.argv[1]).absolute()

        # check / make empty dirs to split JSONs
        passJSON = os.path.join(dir, "passJSON")
        failJSON = os.path.join(dir, "failJSON")

        if not os.path.exists(passJSON):
            os.makedirs(passJSON)

        if not os.path.exists(failJSON):
            os.makedirs(failJSON)

        passed = []
        failed = []

        for files in next(os.walk(dir)):
            for file in files:
                if len(file) == 0:
                    continue
                if file.endswith('.json'):
                    # only check jsons
                    with open(os.path.join(dir, file)) as f:
                        irjson = json.load(f)
                    if valid.validate(irjson) is False:
                        # issue with JSON
                        failed.append(str(file))
                        shutil.move(os.path.join(dir, file), failJSON)
                    else:
                        # JSON good to use
                        passed.append(str(file))
                        shutil.move(os.path.join(dir, file), passJSON)

        print("total passed: ", len(passed))
        print("total failed: ", len(failed))


if __name__ == "__main__":

    valid = validJSON()

    valid.main()
