import argparse
import datetime
import re
import sys
from pyCIPAPI.interpretation_requests import get_interpretation_request_json
from pyCIPAPI.summary_findings import create_flq, create_eq, put_eq, num_existing_reports


def parser_args():
    """Parse arguments from the command line"""
    parser = argparse.ArgumentParser(
        description='Generates a clinical report (summary of findings) for NegNeg reports and submits via CIP API')
    parser.add_argument(
        '-r', '--reporter',
        help='CIP-API user name of person who is generating the report, normally in the format "jbloggs"',
        required=True, type=str)
    parser.add_argument(
        '-d', '--date',
        help='Date in YYYY-MM-DD format recorded in Exit Questionnaire as process date.',
        required=True, type=str)
    parser.add_argument(
        '-t', '--testing',
        help='Flag to use the CIP-API Beta data during testing', action='store_true')
    parser.add_argument(
        '-i', '--interpretation_request',
        help='Interpretation request ID including version number, in the format 11111-1',
        required=True, type=str)
    return parser.parse_args()


def get_request_details(_irid):
    """Check the format of the entered Interpretation request ID and version number"""
    # Regex to check that entered value is digits separated by -
    if not bool(re.match(r"^\d+-\d+$", _irid)):
        sys.exit("Interpretation request ID doesn't match the format 11111-1, please check entry")
    else:
        # If correctly formatted split interpretation_request on '-' and allocate to request_id, request_version
        request_id, request_version = _irid.split('-')
    return request_id, request_version


def main():
    # Parse arguments from the command line
    parsed_args = parser_args()
    # Check interpretation request ID matches expected pattern, and split into ID and version
    ir_id, ir_version = get_request_details(parsed_args.interpretation_request)
    # Get v6 of interpretation request JSON
    ir_json_v6 = get_interpretation_request_json(ir_id, ir_version, reports_v6=True, testing_on=parsed_args.testing)
    # Check that there is only one exisitng clinical report
    if num_existing_reports(ir_json_v6) != 1:
        sys.exit("Expected 1 clinical report but found {num} for interpretation request {ir_id}-{ir_version}".format(
            num=num_existing_reports(ir_json_v6),
            ir_id=ir_id,
            ir_version=ir_version
            )
        )
    # Create exit questionnaire
    eq = create_eq(
        eventDate=parsed_args.date,
        reporter=parsed_args.reporter,
        familyLevelQuestions=create_flq(
            caseSolvedFamily="no",
            segregationQuestion="no",
            additionalComments="No tier 1 or 2 variants detected"
        )
    )
    # Push exit questionnaire to CIP-API
    put_eq(exit_questionnaire=eq, ir_id=ir_id, ir_version=ir_version, testing_on=parsed_args.testing)


if __name__ == '__main__':
    main()
