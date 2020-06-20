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
        proband_call: The variants call for the proband, including zygosity. This data is found under
            the 'variantCalls' key in the interpretation request.
    Attributes:
        data: Report event passed to class constructor
        variant: Variant passed to class constructor
        zygostiy: Zygosity of the variant in the proband e.g. heterozygous
        gene: The gene symbol for the report event variant
        panelname: The panel under which the variant was tiered in this report event
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
    """Determine the tier of a report event.
    
    Args:
        None
    Attributes:
        None
    Methods:
        retier: Implement tiering rules for a given report event variant and panel.
    """
    
    # Regular expressions for comparing mode of inheritance (moi) from the tiering and panelapp.
    #   Keys reperesent tiering moi and regular expression lists represent panelapp mois.
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

    # Define high-impact sequence ontology terms that determine whether variants are high impact.
    #  Keys are sequence ontology IDs while values are tiering output names
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
        """Match a variant's mode of inheritance (tiering_moi) with a gene's mode of inheritance from
        panelapp (pa_moi).
        """
        # If any information on the mode of inheritance is missing, return True.
        # Missing information is defined as empty function inputs, or no regular expression for the
        #  variant's mode of inheritance.
        if (
            tiering_moi is None
            or pa_moi is None
            or tiering_moi.lower() not in self.MOI_REGEX.keys()
        ):
            return True

        # Clean tiering pipeline and panelapp data
        pa_clean = pa_moi.lower().strip().replace(',','').replace(' ','_')
        ti_clean = tiering_moi.lower()

        # Get regular expresssions for the variant's mode of inheritance in panelapp
        regexes = self.MOI_REGEX.get(ti_clean)
        # Return True if the variant's mode of inheritance matches the gene's in panelapp
        any_regex_match = any([ re.search(regex, pa_clean) for regex in regexes ])

        return any_regex_match

    def _is_high_impact(self, segregation: str, consequences: list):
        """Return True if a variant's segregation data or transcript consequences indicate that it is
        a high impact variant.
        """
        if 'denovo' in segregation.lower() or any(
            [ term in self.HIGH_IMPACT_TERMS.keys() for term in consequences ]
        ):
            return True
        else:
            return False

    def retier(self, event: ReportEvent, panel: GeLPanel):
        """Run tiering rules for a report event against a panel app panel.
        Args:
            event(ReportEvent): A GeL tiering pipeline variant report event
            panel(GeLPanel): Object representing a panelapp panel
        Returns:
            retier_result(tuple): Results for the TierUp report. E.g.
                (
                    "tier_1", # A new tiering value assigned by retier() logic
                    "HGNC:175", # HGNC identifier for the gene carrying the variant
                    "ACVRL1", # HGNC symbol for the gene carrying the variant
                    "3", # PanelApp confidence level for the gene carrying the variant
                    "ENSG00000139567", # The Ensembl ID for the gene carrying the variant
                    "MONOALLELIC, autosomal or pseudoautosomal, NOT imprinted"
                        # ^PanelApp mode of inheritance for disease-causing variants in this gene
                )
        """
        # Query the current version of the panel in panel app. Returns details of the gene.
        hgnc, symbol, gene_confidence, ensembl, pa_moi = panel.query(event.ensembl)
        # If the gene is not in this panel: tier_3_not_in_panel
        if gene_confidence is None:
            tiering_result = 'tier_3_not_in_panel'
        # If the gene confidence level is not green (3,4): tier_3_red_or_amber
        elif gene_confidence not in ['3', '4']:
            tiering_result = 'tier_3_red_or_amber'
        # If variant's mode of inheritance does not match the gene's in panel app: tier_3_green_moi_mismatch
        elif not self._moi_match(event.data['modeOfInheritance'], pa_moi):
            tiering_result = 'tier_3_green_moi_mismatch'
        # If the variant and gene mode of inheritance match, but the variant consequence is not high
        #   impact: tier_2
        elif not self._is_high_impact(
            event.data["segregationPattern"],
            [ cons['id'] for cons in event.data["variantConsequences"] ]
        ):
            tiering_result = 'tier_2'
        # If all the above is false, the variant is Tier 1. The variant is in a green gene in panel
        #  app, matches the disease mode of inheritance and has a high impact consequence 
        else:
            tiering_result = 'tier_1'
        
        return tiering_result, hgnc, symbol, gene_confidence, ensembl, pa_moi
         

class TierUpRunner:
    """Run TierUp on an interpretation request json object.
    Args:
        TL(TieringLite): An object with a `retier` method for applying tiering rules to report events. 
    """

    def __init__(self, TL=TieringLite):
        self.tiering_lite = TL()

    def run(self, irjo:IRJson):
        """Run TierUp.
        Args:
            irjo: Interpretation request json object
        """
        proband_report_events = self._get_proband_report_events(irjo)
        for event in proband_report_events:
            # Try to get a jellypy.tierup.panelapp.GeLPanel object for the variants panel. These are
            # stored under the irjo.panels dictionary.
            try:
                panel = irjo.panels[event.panelname]
            except KeyError:
                # If there is no matching panel, log warning and move onto the next report event.
                logger.warning(
                    f'A report event panel could not be found in the irjson object:'
                    f' event panel is {event.panelname}, loaded irjson panels are {irjo.panels.keys()}'
                )
                continue
            
            # Retier the variant against the latest version of the panel. Returns:
            #  (new_tier, hgnc, symbol, gene_confidence, ensembl_id, panelapp_mode_of_inheritance)
            retier_result = self.tiering_lite.retier(event, panel)

            # Return a tierup output record
            record = self.tierup_record(event, panel, irjo, retier_result)
            yield record

    def _get_proband_report_events(self, irjo):
        """Return report events for any variants in the proband."""
        # Gather all report events and the variant objects they are nested in in a tuple.
        for variant in irjo.tiering["interpreted_genome_data"]["variants"]:
            for event in variant["reportEvents"]:
                # Search for any proband variant calls in the variant report events.
                proband_call_list = [
                    vcall for vcall in variant['variantCalls']
                    if vcall and vcall['participantId'] == irjo.proband_id
                ]
                # If this event's variant is in the proband, return a ReportEvent object
                if proband_call_list:
                    proband_call = proband_call_list.pop()
                    yield ReportEvent(event, variant, proband_call)

    def tierup_record(self, event, panel, irjo, retier_result):
        """Return TierUp dict result for a Tier 3 variant"""
        tier, hgnc, hgnc_symbol, pa_gene_confidence, ensembl_id, pa_moi = retier_result
        record = {
            # Note: Keys in the record form the header line of the tierup output. We prepend '#'to
            # the first entry so that it can easily be filtered away.
            "#interpretation_request_id": irjo.tiering["interpreted_genome_data"][
                "interpretationRequestId"
            ],
            "tier_tierup": tier,
            "tier_gel": event.data["tier"],
            "assembly": event.variant["variantCoordinates"]["assembly"],
            "chromosome": event.variant["variantCoordinates"]["chromosome"],
            "position": event.variant["variantCoordinates"]["position"],
            "reference": event.variant["variantCoordinates"]["reference"],
            "alternate": event.variant["variantCoordinates"]["alternate"],
            "consequences": ",".join(
                [ 
                    ":".join(vc.values()) for vc in event.data["variantConsequences"]
                ]
            ),
            "zygosity": event.zygosity,
            "segregation": event.data["segregationPattern"],
            "penetrance": event.data["penetrance"],
            "tiering_moi": event.data["modeOfInheritance"],
            "tu_panel_hash": panel.hash,
            "tu_panel_name": panel.name,
            "tu_panel_version": panel.version,
            "tu_panel_number": panel.id,
            "tu_panel_created": panel.created,
            "tu_run_time": datetime.datetime.now().strftime("%c"),
            "pa_ensembl": ensembl_id,  
            "pa_hgnc_id": hgnc,
            "pa_gene": hgnc_symbol,
            "pa_moi": pa_moi,
            "pa_confidence": pa_gene_confidence,
            "extra_panels": irjo.updated_panels,      
            "re_id": event.data["reportEventId"],
            "re_panel_id": event.data["genePanel"]["panelIdentifier"],
            "re_panel_version": event.data["genePanel"]["panelVersion"],
            "re_panel_source": event.data["genePanel"]["source"],
            "re_panel_name": event.data["genePanel"]["panelName"],
            "re_gene": event.gene,
            "justification": event.data["eventJustification"],
            "created_at": irjo.tiering["created_at"],            
            "software_versions": str(
                irjo.tiering["interpreted_genome_data"]["softwareVersions"]
            ),
            "reference_db_versions": str(
                irjo.tiering["interpreted_genome_data"]["referenceDatabasesVersions"]
            ),            
            "tu_version": pkg_resources.require("jellypy-tierup")[0].version,
        }
        return record


class TierUpCSVWriter():
    """Write TierUp results as CSV file.

    Args:
        outfile(str): Output file path
        schema(str): A json.schema file with output file headers expected in data
        writer(csv.DictWriter): An object for writing dictionaires as csv data
    """
    schema = pkg_resources.resource_string("jellypy.tierup", "data/report.schema")

    def __init__(self, outfile, writer=csv.DictWriter):
        self.outfile = outfile
        self.outstream = open(outfile, "w")
        self.header = json.loads(self.schema)["required"]
        self.writer = writer(self.outstream, fieldnames=self.header, delimiter="\t")
        self.writer.writeheader()

    def write(self, data: list):
        """Write data to csv output file"""
        for record in data:
            self.writer.writerow(record)

    def close_file(self):
        """Close csv output file"""
        self.outstream.close()
