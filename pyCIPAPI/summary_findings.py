"""
Functions for creating a clinical report (aka summary of findings). This is designed to emulate the closing of a case via the interpretation portal.
"""
import datetime
from protocols.reports_6_0_0 import ClinicalReport, InterpretedGenome
from .auth import AuthenticatedCIPAPISession
from .config import live_100k_data_base_url, beta_testing_base_url

def create_cr(
    interpretationRequestId,
    interpretationRequestVersion,
    reportingDate,
    user,
    genomicInterpretation,
    referenceDatabasesVersions,
    softwareVersions,
    variants=[],
    structuralVariants=[], 
    chromosomalRearrangements=None,
    shortTandemRepeats=[],
    uniparentalDisomies=None,
    karyotypes=None,
    additionalAnalysisPanels=None,
    references=[]
    ):
    """Create a GeL Report Models v6 Clinical Report (aka Summary of Findings)
    
    See here for field definitions: 
    https://gelreportmodels.genomicsengland.co.uk/html_schemas/org.gel.models.report.avro/6.0.1/ClinicalReport.html#/schema/org.gel.models.report.avro.ClinicalReport
    
    When closing a case with no variants through the interpretation portal, it was noted in the clinical report JSON that some fields were entered as an empty list whereas others were nulls. 
    The mix of empty lists and 'None' types in the default values for this function is designed to mirror this.

    Args:
        interpretationRequestId: string (required)
        interpretationRequestVersion: integer (required)
        reportingDate: string (required)
        user: string (required)
        variants: list (optional)
        structuralVariants: list (optional)
        chromosomalRearrangements: list (optional)
        shortTandemRepeats: list (optional)
        uniparentalDisomies: list (optional)
        karyotypes: list (optional)
        genomicInterpretation: string (required)
        additionalAnalysisPanels: list (optional)
        references: string (optional)
        referenceDatabasesVersions: dictionary (required) - Use get_reference_db_versions()
        softwareVersions: dictionary (required) - Use gel_software_versions()
    """
    # Check date in correct format (YYYY-MM-DD) by converting to datetime object 
    reportingDate = datetime.datetime.strptime(reportingDate, "%Y-%m-%d")
    # Then convert back to string ready for submission
    reportingDate = reportingDate.strftime("%Y-%m-%d")
    # Create the ClinicalReport object
    cr = ClinicalReport(
        interpretationRequestId=interpretationRequestId,
        interpretationRequestVersion=int(interpretationRequestVersion),
        reportingDate=reportingDate,
        user=user,
        variants=variants,
        structuralVariants=structuralVariants,
        chromosomalRearrangements=chromosomalRearrangements,
        shortTandemRepeats=shortTandemRepeats,
        uniparentalDisomies=uniparentalDisomies,
        karyotypes=karyotypes,
        genomicInterpretation=genomicInterpretation,
        additionalAnalysisPanels=additionalAnalysisPanels,
        references=references,
        referenceDatabasesVersions=referenceDatabasesVersions,
        softwareVersions=softwareVersions
        )
    # Check clinical report object is valid using inbuilt validate method. Report errors if not.
    if not cr.validate(cr.toJsonDict()):
        raise TypeError("Clinical report object not valid. See details:\n{message}".format(message=cr.validate(cr.toJsonDict(), verbose=True).messages))
    else:
        return cr

def post_cr(ir_json_v6, clinical_report, testing_on=False):
    """
    Submit clinical report (aka summary of findings) to CIP-API. 
    This uses genomics_england_tiering as the analysis partner, emulating the closing of a case through the interpretation portal
    Args:
        ir_json_v6 = get using interpretation_requests.get_interpretation_request_json() with reports_v6=True 
        clinical_report = populated clinical report object output from create_cr()
        testing_on = setting to True will use beta cip-api rather than live
    """
    # Get the full interpretation request ID (including cip prefix and version e.g. SAP-12345-1) 
    ir_id = ir_json_v6.get('case_id')
    # Create endpoint from user supplied variables ir_id and ir_version (hardcoded clinical_report_version 1 is OK
    # because script checks no other clinical reports have been generated before calling this function:
    cr_endpoint = "clinical-report/genomics_england_tiering/raredisease/{ir_id}/?reports_v6=true".format(
        ir_id=ir_id
        )
    # Set base url based on testing status
    if testing_on:
        cip_api_url = beta_testing_base_url
    else:
        cip_api_url = live_100k_data_base_url  
    # Create urls for uploading exit questionnaire and summary of findings
    summary_of_findings_url = cip_api_url + cr_endpoint
    # Open Authenticated CIP-API session:
    gel_session = AuthenticatedCIPAPISession(testing_on=testing_on)
    # Upload Summary of findings:    
    response = gel_session.post(url=summary_of_findings_url, json=clinical_report.toJsonDict())
    # Raise error if unsuccessful status code returned
    response.raise_for_status()

def num_existing_reports(ir_json_v6):
    """
    This returns the number of existing clinical reports (i.e. summary of findings) for a case
    This can be used to check that there aren't any existing clinical reports before submitting a new one,
    or to check that there is only one clinical report when submitting an exit questionnaire
    """
    return len(ir_json_v6.get("clinical_report"))

def get_ref_db_versions(ir_json_v6):
    """
    This returns a dictionary that can be submitted for the referenceDatabasesVersions field of clinical report
    When closing a case through the interpretation portal, only the genomeAssembly is included in this dictionary
    This function will pull out the genomeAssembly from the ir json
    """
    return {"genomeAssembly": ir_json_v6.get('assembly')}

def gel_software_versions(ir_json_v6):
    """
    This returns a dictionary that can be submitted for the softwareVersions field of clinical report
    This function will pull out the softwareVersions from the genomics_england_tiering interpreted genome 
    (equivalent to creating summary of findings in the interpretation portal)
    """
    #Loop through interpreted genomes, and pull out softwareVersions from the genomics_england_tiering interpreted genome
    interpreted_genomes = ir_json_v6['interpreted_genome']
    for ig in interpreted_genomes:
        ig_obj = InterpretedGenome.fromJsonDict(ig['interpreted_genome_data'])
        cip = ig_obj.interpretationService.lower()
        if cip == 'genomics_england_tiering':
            return ig_obj.softwareVersions