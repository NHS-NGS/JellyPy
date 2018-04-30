import datetime
import json
from pyCIPAPI.interpretation_requests import (
    get_interpretation_request_list, get_interpretation_request_json)


def main():
    interpretation_requests_list = get_interpretation_request_list()
    for case in interpretation_requests_list:
        count_tiered_variants(case)
    output_tsv(interpretation_requests_list)
    output_json(interpretation_requests_list)


def count_tiered_variants(case):
    case['T1'] = 0
    case['T2'] = 0
    case['T3'] = 0
    ir_id, ir_version = case['interpretation_request_id'].split('-')
    interpretation_request = get_interpretation_request_json(ir_id, ir_version)
    case['interpretation-request_data'] = interpretation_request
    for variant in (interpretation_request['interpretation_request_data']
                    ['json_request']['TieredVariants']):
        tiering = []
        for reportevent in variant['reportEvents']:
            re_tier = int(reportevent['tier'].strip('TIER'))
            tiering.append(re_tier)
        tier = min(tiering)
        case['T{}'.format(tier)] += 1


def output_tsv(interpretation_requests_list):
    output_file = ('{}_interpretation_request_audit.tsv'
                   .format(datetime.datetime.today().strftime('%Y%m%d')))
    with open(output_file, 'w') as fout:
        for case in interpretation_requests_list:
            line = ('\t'.join(
                    [str(n) for n in [
                        case['family_id'], case['number_of_samples'],
                        ','.join(case['sites']), case['sample_type'],
                        case['T1'], case['T2'], case['T3']]]))
            fout.write(line + '\n')


def output_json(interpretation_requests_list):
    output_file = ('{}_interpretation_request_audit.json'
                   .format(datetime.datetime.today().strftime('%Y%m%d')))
    with open(output_file, 'w') as fout:
        json.dump(interpretation_requests_list, fout)


if __name__ == '__main__':
    main()
