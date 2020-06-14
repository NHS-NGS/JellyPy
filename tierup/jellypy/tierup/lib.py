import datetime
import pkg_resources
import json
import logging
import csv
import re

from jellypy.tierup.irtools import IRJson
from jellypy.tierup.panelapp import PanelApp, GeLPanel

logger = logging.getLogger(__name__)


class ReportEvent:
    """Data objects for a GeL tiering report event.

    Args:
        event: A report event from the irjson tiering section
        variant: The variant under which the report event is nested in the irjson
        proband_calls: variantCalls data for the proband
    Attributes:
        data: Report event passed to class constructor
        variant: Variant passed to class constructor
        gene: The gene symbol for the tiered report event variant
        panelname: The panel name relevant to the report event variant
    """

    def __init__(self, event, variant, proband_call ):
        self.data = event
        self.variant = variant
        self.zygosity = proband_call['zygosity']
        self.gene = self._get_gene()
        self.ensembl = self._get_gene(ensembl_id=True)
        self.panelname = self.data["genePanel"]["panelName"]

    def _get_gene(self, ensembl_id=False):
        """Returns the gene symbol from a GeL report event"""
        identifier = "ensemblId" if ensembl_id else "geneSymbol"
        all_genes = [
            entity[identifier]
            for entity in self.data["genomicEntities"]
            if entity["type"] == "gene"
        ]
        # Add check. Report events cannot have more than one gene.
        assert len(all_genes) == 1, "More than one report event entity of type gene"
        return all_genes.pop()

class PanelUpdater:
    """Update panel IDs in IRJson object panels.

    Panels applied when tier 3 variants were reported can have different PanelApp IDs today.
    This class searches PanelApp to update panel identifiers where possible.
    """

    def __init__(self):
        pass

    def add_event_panels(self, irjo: IRJson) -> None:
        """Add new panel identifiers to IRJson objects where panels have been merged.
        This updates the ID of renamed or merged panels, ensuring the accurate current panel is returned
        from any downstream PanelApp API calls.

        Args:
            irjo: An interpretation request json object
        """
        missing_panels = self._find_missing_event_panels(irjo)
        panels_to_add = self._search_panelapp(missing_panels)
        for name, identifier in panels_to_add:
            irjo.update_panel(name, identifier)

    def _search_panelapp(self, missing_panels) -> list:
        """Search the relevant disorders section of panelapp for given panel names.

        Args:
            missing_panels: Panel names to find in panelapp.
        Returns:
            List[Tuple]: A list of tuples containing the panel name and relevant ID.
        """
        oldname_id = []
        # for panel in panel app;
        pa = PanelApp()
        for gel_panel in pa:
            for panel_name in missing_panels:
                if panel_name in gel_panel["relevant_disorders"]:
                    # Note assumption: All panel names have one ID matching in panel app
                    oldname_id.append((panel_name, gel_panel["id"]))
        return oldname_id

    def _find_missing_event_panels(self, irjo) -> set:
        """Find panels reported with variants at the time of tiering but missing from the
        interpretation request panels listing, which is kept up to date.

        Args:
            irjo: An interpretation request json object
        Returns:
            A set of panel names missing from the top-level of the interpretation request. These names
                have likely been updated and filed uner a new panel ID.
        """
        event_panels = {
            event["genePanel"]["panelName"]
            for variant_data in irjo.tiering["interpreted_genome_data"]["variants"]
            for event in variant_data["reportEvents"]
        }
        ir_panels = set(irjo.panels.keys())
        return event_panels - ir_panels

class TieringLite():
    """Determine tier of a report event"""
    
    MOI_REGEX = {
        "biallelic": [r'^biallelic', r'.*monoallelic_and_biallelic', r'^unknown', r'^other'],
        "xlinked_biallelic": [r'x.linked.*biallelic', r'^unknown', r'^other'],
        "denovo": [r'monoallelic',r'x.linked', r'.*mitochondrial',r'^unknown', r'^other'],
        "xlinked_monoallelic": [r'x.linked.*', r'^unknown', r'^other'],
        "monoallelic": [r'monoallelic', r'x.linked', r'mitochondrial',r'^unknown', r'^other'],
        "monoallelic_not_imprinted": [r'monoallelic', r'x.linked', r'mitochondrial',r'^unknown', r'^other'],
        "monoallelic_paternally_imprinted": [r'monoallelic.*paternally', r'^unknown', r'^other'],
        "monoallelic_maternally_imprinted": [r'monoallelic.*maternally', r'^unknown', r'^other'],
        "mitochondrial": [r'mitochondrial', r'^unknown', r'^other']
    }

    HIGH_IMPACT_TERMS = {
        "SO:0001893": 'transcript_ablation',
        "SO:0001574": 'splice_acceptor_variant',
        "SO:0001575": 'splice_donor_variant',
        "SO:0001587": 'stop_gained',
        "SO:0001589": 'frameshift_variant',
        "SO:0001578": 'stop_lost',
        "SO:0001582": 'initiator_codon_variant'
    }

    def __init__(self):
        pass

    def _moi_match(self, tiering_moi, pa_moi):
        #NOTE; Should work on principle: If we have a record for it, check it. Otherwise let it through.
        if tiering_moi is None or pa_moi is None or tiering_moi.lower() not in self.MOI_REGEX.keys():
            return True

        pa_clean = pa_moi.lower().strip().replace(',','').replace(' ','_')
        ti_clean = tiering_moi.lower()

        return any([ re.search(pa_moi_regex, pa_clean) for pa_moi_regex in self.MOI_REGEX.get(ti_clean, ['.*']) ])

    def _is_high_impact(self, segregation, consequences):
        if 'denovo' in segregation.lower() or any(
            [ term in self.HIGH_IMPACT_TERMS.keys() for term in consequences ]
        ):
            return True
        else:
            return False

    def retier(self, event: ReportEvent, panel: GeLPanel):
        hgnc, symbol, conf, ensembl, pa_moi = panel.query(event.ensembl)
    #     # If pa confidence is blank; tier_3_not_in_panel
        if conf is None:
            return 'tier_3_not_in_panel' 
    #     # If pa confidence is less than three; tier_3_red_or_amber
        elif conf not in ['3', '4']:
            return 'tier_3_red_or_amber'
    #     # If pa confidence is 3 or 4 AND
    #         # If mode of inheritance violates; tier_3_green_moi_mismatch
        elif not self._moi_match(event.data['modeOfInheritance'], pa_moi):
            return 'tier_3_green_moi_mismatch'
    #   # If not high impact and moi; tier_2
        elif not self._is_high_impact(
            event.data["segregationPattern"],
            [ cons['id'] for cons in event.data["variantConsequences"] ]
        ):
            return 'tier_2'
        elif conf in ['3','4'] and self._moi_match(event.data['modeOfInheritance'], pa_moi
            ) and self._is_high_impact(
            event.data["segregationPattern"],
            [ cons['id'] for cons in event.data["variantConsequences"] ]
        ):
            return 'tier_1'
        else:
            return 'error_unable_to_tier'

class TierUpRunner:
    """Run TierUp on an interpretation request json object"""

    def __init__(self, tiering_lite=TieringLite):
        self.tl = TieringLite()

    def run(self, irjo):
        """Run TierUp.
        Args:
            irjo: Interpretation request json object
        """
        tier_three_events = self.generate_events(irjo)
        for event in tier_three_events:
            panel = irjo.panels[event.panelname]
            hgnc, symbol, conf, ensembl, pa_moi = panel.query(event.ensembl)
           # if self.tl.moi_match(event.data['modeOfInheritance'], pa_moi): # Change to new annotation if this works
            record = self.tierup_record(event, hgnc, conf, panel, irjo)
            yield record

    def generate_events(self, irjo):
        """Return report event objects for all Tier 3 variants found in the proband"""
        # Gather all report events and the variant objects they are nested in in a tuple.
        for variant in irjo.tiering["interpreted_genome_data"]["variants"]:
            for event in variant["reportEvents"]:
                # Search for any proband variant calls. These are labelled by paricipant ID within the
                #    variant dictionary 
                proband_call_list = [
                    vcall for vcall in variant['variantCalls']
                    if vcall and vcall['participantId'] == irjo.proband_id
                ]
                # If there is tier 3 report event and a variant call in the proband, return a ReportEvent
                if event["tier"] == "TIER3" and proband_call_list:
                    proband_call = proband_call_list.pop()
                    yield ReportEvent(event, variant, proband_call)

    def tierup_record(self, event, hgnc, confidence, panel, irjo):
        """Return TierUp dict result for a Tier 3 variant"""
        record = {
            "justification": event.data["eventJustification"],
            "consequences": str(
                [cons["name"] for cons in event.data["variantConsequences"]]
            ),
            "penetrance": event.data["penetrance"],
            "denovo_score": event.data["deNovoQualityScore"],
            "score": event.data["score"],
            "event_id": event.data["reportEventId"],
            "interpretation_request_id": irjo.tiering["interpreted_genome_data"][
                "interpretationRequestId"
            ],
            "created_at": irjo.tiering["created_at"],
            "tier": event.data["tier"],
            "segregation": event.data["segregationPattern"],
            "inheritance": event.data["modeOfInheritance"],
            "group": event.data["groupOfVariants"],
            "zygosity": event.zygosity,
            "position": event.variant["variantCoordinates"]["position"],
            "chromosome": event.variant["variantCoordinates"]["chromosome"],
            "assembly": event.variant["variantCoordinates"]["assembly"],
            "reference": event.variant["variantCoordinates"]["reference"],
            "alternate": event.variant["variantCoordinates"]["alternate"],
            "re_panel_id": event.data["genePanel"]["panelIdentifier"],
            "re_panel_version": event.data["genePanel"]["panelVersion"],
            "re_panel_source": event.data["genePanel"]["source"],
            "re_panel_name": event.data["genePanel"]["panelName"],
            "re_gene": event.gene,
            "tu_panel_hash": panel.hash,
            "tu_panel_name": panel.name,
            "tu_panel_version": panel.version,
            "tu_panel_number": panel.id,
            "tu_panel_created": panel.created,
            "pa_hgnc_id": hgnc,
            "pa_gene": event.gene,
            "pa_confidence": confidence,
            "software_versions": str(
                irjo.tiering["interpreted_genome_data"]["softwareVersions"]
            ),
            "reference_db_versions": str(
                irjo.tiering["interpreted_genome_data"]["referenceDatabasesVersions"]
            ),
            "extra_panels": irjo.updated_panels,
            "tu_run_time": datetime.datetime.now().strftime("%c"),
            "tier1_count": irjo.tier_counts["TIER1"],
            "tier2_count": irjo.tier_counts["TIER2"],
            "tier3_count": irjo.tier_counts["TIER3"],
            "tu_version": pkg_resources.require("jellypy-tierup")[0].version
        }
        return record


class TierUpWriter:
    """Write TierUp results as CSV file.

    Args:
        outfile(str): Output file path
        schema(str): A json.schema file with output file headers expected in data
        writer(csv.DictWriter): An object for writing dictionaires as csv data
    """

    def __init__(self, outfile, schema, writer=csv.DictWriter):
        self.outfile = outfile
        self.outstream = open(outfile, "w")
        self.header = json.loads(schema)["required"]
        self.writer = writer(self.outstream, fieldnames=self.header, delimiter="\t")

    def write(self, data):
        """Write data to csv output file"""
        self.writer.writerow(data)

    def close_file(self):
        """Close csv output file"""
        self.outstream.close()


class TierUpCSVWriter(TierUpWriter):
    """TierUp report csv writer.  Writes all Tier3 variants analysed"""

    schema = pkg_resources.resource_string("jellypy.tierup", "data/report.schema")

    def __init__(self, *args, **kwargs):
        super(TierUpCSVWriter, self).__init__(*args, schema=self.schema, **kwargs)
        self.writer.writeheader()


class TierUpSummaryWriter(TierUpWriter):
    """TierUp summary report writer. Writes only Tier3 variants that have increased Tier"""

    schema = pkg_resources.resource_string(
        "jellypy.tierup", "data/summary_report.schema"
    )

    def __init__(self, *args, **kwargs):
        super(TierUpSummaryWriter, self).__init__(*args, schema=self.schema, **kwargs)

    def write(self, data):
        if data["pa_confidence"] and data["pa_confidence"] in ["3", "4"]:
            filtered = {k: v for k, v in data.items() if k in self.header}
            self.writer.writerow(filtered)
