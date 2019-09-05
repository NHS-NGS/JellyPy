import argparse
from time import strptime
from datetime import date, timedelta
import os
import pandas as pd
from pyCIPAPI.interpretation_requests import access_date_summary_content, get_interpreted_genome_for_case, \
    get_interpretation_request_list


def parser_args():
    """Parse arguments from the command line"""
    parser = argparse.ArgumentParser(
        description='Generates a summary of cancer cases within the specified time period with Pharma. variants')
    parser.add_argument(
        '-d', '--delta', type=int,
        help='number of days back from today which should be checked, optional if specific dates are set instead', )
    parser.add_argument('-d1', '--date1', help='First date in in DD-MM-YYYY format, inclusive', type=str, default='X')
    parser.add_argument('-d2', '--date2', help='First date in in DD-MM-YYYY format, inclusive', type=str, default='X')
    parser.add_argument('-t', '--testing', help='Flag to use the CIP-API Beta data during testing', action='store_true')
    parser.add_argument('-o', '--output_prefix', help='Name of output file to be generated if cases are found',
                        type=str)
    return parser.parse_args()


def get_dpyd_cases(case_list, testing):
    """
    Takes a list of cases, tries to find an interpreted genome for the pharma service, and checks if present
    at time of writing, any pharma variants are DPYD, more granular check may be required in future
    :param case_list: list of case strings in IR-VER format
    :return:
    """

    dpyd_cases = []

    for case in case_list:
        ir, ver = case.split('-')

        pharma_genome = get_interpreted_genome_for_case(ir=ir, version=ver,
                                                        tiering_service='genomics_england_pharmacogenomics',
                                                        testing_on=testing)

        if not pharma_genome:
            continue

        elif pharma_genome == {'detail': 'Not found.'}:
            continue

        # print(pharma_genome)

        if pharma_genome['interpreted_genome_data']['variants']:
            if len(pharma_genome['interpreted_genome_data']['variants']) > 0:
                dpyd_cases.append(case)

    return dpyd_cases


def create_filename(parsed_args):
    """
    Uses a few inputs to make a horrible verbose name
    :return:
    """

    filename = 'DPYD_pharma_cases_{days}_days_up_to_{date}'.format(
        days=parsed_args.delta,
        date=str(date.today())
    )

    return filename


def assemble_output(dpyd_cases, output_name, testing):
    """

    :param dpyd_cases:
    :param output_name:
    :return:
    """

    case_count_df = pd.DataFrame(columns=["case_id", "Participant", "LDP"])

    if os.path.exists(output_name + '.xlsx'):
        response_string = '{} exists, do you want to overwrite it?\n(y/n)\n'.format(output_name + '.xlsx')
        try:
            response = input(response_string)
        except:
            response = raw_input(response_string)

        if not 'y' in response.lower():
            print('won\t overwrite file, printing DPYD cases instead')
            for case in dpyd_cases:
                print(case)
            quit()

    # provided we're not overwriting files and there are cases to write, write them!
    for count, case in enumerate(dpyd_cases):
        # get the minimmal endpoint details for a single case - could try/except wrap, but should work
        case_json = get_interpretation_request_list(interpretation_request_id=case.split('-')[0], testing_on=testing)[0]
        ldp = case_json['sites'][0]
        proband = case_json['proband']
        case_count_df.loc[count] = [case, proband, ldp]  # lookup of LDP to GMC shouldn't be required at GMC level

    case_count_df.to_excel(excel_writer=output_name + '.xlsx', sheet_name='DPYD_cases', index=False)


if __name__ == '__main__':
    # Parse arguments from the command line
    parsed_args = parser_args()

    cases_to_check = []

    # check if we are using a delta or a pair of dates
    if parsed_args.delta:
        today = date.today()
        print('Check will be for a period of {days} days leading up to {today}'.format(days=parsed_args.delta,
                                                                                       today=str(today)))
        date1 = (today - timedelta(days=parsed_args.delta)).strftime('%d-%m-%Y')
        date2 = today.strftime('%d-%m-%Y')

        response_cases = access_date_summary_content(date1=date1, date2=date2, testing_on=parsed_args.testing)['cases']

    # otherwise we need to take user specified dates
    else:

        if parsed_args.date1 == 'X' or parsed_args.date2 == 'X':
            raise AssertionError('At least one of the required dates was not provided, '
                                 'Either supply two dates, or a number of days to check using "-d"')

        try:
            assert strptime(parsed_args.date1, '%d-%m-%Y') < strptime(parsed_args.date2, '%d-%m-%Y'), \
                'Dates provided in wrong order'
        except ValueError as v:
            print('Date Values provided couldn\'t be converted:', v)
            quit()

        response_cases = \
        access_date_summary_content(date1=parsed_args.date1,
                                    date2=parsed_args.date2,
                                    testing_on=parsed_args.testing)['cases']

    if 'illumina-sent_to_gmcs' in response_cases.keys():
        cases_to_check = response_cases['illumina-sent_to_gmcs']
        print('{} New cases identified, checking for Pharmacogenomic results..'.format(len(cases_to_check)))

    else:
        print('No cases were identified within the specified time period')
        quit()

    dpyd_cases = get_dpyd_cases(cases_to_check, parsed_args.testing)

    if not dpyd_cases:
        print('None of the {num} cases during this time period contain DPYD variants'.format(num=len(cases_to_check)))
        quit()

    if not parsed_args.output_prefix:
        parsed_args.output_prefix = create_filename(parsed_args)

    # might wanna amend this method to export cases checked and cases positive, indicator in output
    assemble_output(dpyd_cases, parsed_args.output_prefix, parsed_args.testing)
