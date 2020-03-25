import datetime
from jellypy.pyCIPAPI.interpretation_requests import (
    get_interpretation_request_list, get_interpretation_request_json,
    get_variant_tier, save_interpretation_request_list_json)


def _main():
    interpretation_requests_list = get_interpretation_request_list()
    for case in interpretation_requests_list:
        count_tiered_variants(case)
    output_tsv(interpretation_requests_list)
    save_interpretation_request_list_json(interpretation_requests_list)


def count_tiered_variants(case):
    """Count the number of variants in each tier for a case."""
    case['T1'] = 0
    case['T2'] = 0
    case['T3'] = 0
    ir_id, ir_version = case['interpretation_request_id'].split('-')
    interpretation_request = get_interpretation_request_json(ir_id, ir_version)
    case['interpretation-request_data'] = interpretation_request
    for variant in (interpretation_request['interpretation_request_data']
                    ['json_request']['TieredVariants']):
        tier = get_variant_tier(variant)
        case['T{}'.format(tier)] += 1


def output_tsv(interpretation_requests_list):
    """Output a date stamped TSV file of the interpretation_requests_list.

    Output file fields: Gel Family ID, Number of samples, Site(s), Sample Type,
    Tier 1, Tier 2, and Tier 3 variant counts.
    """
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


if __name__ == '__main__':
    _main()
