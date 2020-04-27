import logging
import pathlib

from jellypy.tierup import lib
from jellypy.tierup import interface
from jellypy.pyCIPAPI.auth import AuthenticatedCIPAPISession
from jellypy.tierup.irtools import IRJIO

logger = logging.getLogger(__name__)


def set_irj_object(irjson, irid, irversion, config):
    if irjson:
        logger.info(f'Reading from local file: {irjson}')
        irjo = IRJIO.read(irjson)
    elif irid and irversion:
        logger.info(f'Downloading from CIPAPI: {irid}-{irversion}')
        sess = AuthenticatedCIPAPISession(
            auth_credentials={
                'client_id': config.get('pyCIPAPI', 'client_id'),
                'client_secret': config.get('pyCIPAPI', 'client_secret')
            }
        )
        irjo = IRJIO.get(irid, irversion, sess)
    else:
        raise Exception('Invalid arguments. If irjson is None, irid and irversion must both be supplied.')
    return irjo

def main(config, irid, irversion, irjson, outdir):
    """Call TierUp and write results to output directory.

    If `irid` and `irversion` are supplied, cased data is pulled from the CIP-API for TierUp.
    Alternatively, a local interpretation request json file can be used via the `irjson` argument.
     
    Args:
        config(dict): A config parser config object parsed from a jellypy config.ini
        irid(int): Interpretation request id e.g. 1234
        irversion(int): Interpretation request version e.g. 1
        irjson(str): Path to a local interpretation request json file e.g. "jsons/local/1234-1.json"
        outdir(str): Output directory for tierup results
    """
    pathlib.Path(outdir).mkdir(parents=True, exist_ok=True)
    irjo = set_irj_object(irjson, irid, irversion, config)
    if not irjson:
        logger.info(f'Saving IRJson to output directory.')
        IRJIO.save(irjo, outdir=outdir)

    logger.info('Searching for merged PanelApp panels')
    lib.PanelUpdater().add_event_panels(irjo)

    logger.info(f'Running tierup for {irjo}')
    records = lib.TierUpRunner().run(irjo)

    logger.info(f'Writing results to: {csv_writer.outfile}, {summary_writer.outfile}')
    csv_writer = lib.TierUpCSVWriter(outfile=pathlib.Path(outdir, irjo.irid + ".tierup.csv"))
    summary_writer = lib.TierUpSummaryWriter(outfile=pathlib.Path(outdir, irjo.irid + ".tierup.summary.csv"))

    for record in records: # Records is a generator of tierup results exhausted in one loop.
        csv_writer.write(record)
        summary_writer.write(record)

    csv_writer.close_file()
    summary_writer.close_file()

    logger.info('END')

if __name__ == "__main__":
    interface.cli()
