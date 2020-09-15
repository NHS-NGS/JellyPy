"""
Functions to handle importing sample analysis in to database.
Expects a dictionary of variant details, plus related objects containing
information for clinvar and hgmd etc.

Jethro Rainford
jethro.rainford@addenbrookes.nhs.uk
200625
"""

import datetime
import os
import sys
import mysql.connector as mysql

try:
    from db_credentials import db_credentials
except ImportError:
    print("Database credentials must be first defined. Exiting.")
    sys.exit()


class SQLQueries(object):

    def __init__(self, db_credentials):
        """
        Open connection to database
        Initialises self.cursor object to perform queries in other functions

        Args:
            - db_credentials (dict): credentials to connect to MySQL DB

        Returns: None
        """

        self.db = mysql.connect(
            host=db_credentials["host"],
            user=db_credentials["user"],
            passwd=db_credentials["passwd"],
            database=db_credentials["database"],
            autocommit=True
        )
        self.cursor = self.db.cursor(buffered=True)


    def __enter__(self):
        return self


    def get_analysis_run(self, cursor):
        """
        Check last analysis_run value and returns =+1

        Args:
            - cursor: MySQL connector object

        Returns:
            - analysis_id (int): number for new analysis run, used by
              all samples being analysed in the same instance
              (arg for save_to_analysis())
        """

        cursor.execute(
            "SELECT analysis_id FROM analysis ORDER BY analysis_id\
                DESC LIMIT 1"
        )
        last_run = cursor.fetchone()[0]

        print("last run: ", last_run)

        if last_run:
            # get last run and increase by 1
            analysis_id = int(last_run) + 1
        else:
            # empty table, start at 1
            analysis_id = 1

        print("new run: ", analysis_id)

        return analysis_id


    def save_analysis(self, cursor, analysis_id, clinvar_ver, hgmd_ver):
        """
        Saves to analysis table.
        Stores analysis id, analysis date, clinvar ver. & HGMD ver.

        Args:
            - cursor: MySQL connector object
            - analysis_id (int): id of analysis run from analysis table
            - clinvar_ver (str): version of ClinVar VCF used
            - hgmd_ver (str): version of HGMD VCF used

        Returns: None
        """
        today = datetime.datetime.now().strftime('%Y-%m-%d')

        query = """
                INSERT INTO analysis
                    (analysis_id, analysis_date, clinvar_ver, hgmd_ver)
                VALUES
                    (%s, %s, %s, %s)
                """
        data = (analysis_id, today, clinvar_ver, hgmd_ver)

        cursor.execute(query, data)


    def save_sample(self, cursor, ir_id):
        """
        Checks if ir ID exists in db already, if it does just update
        date last analysed, if not add as new record. Returns id of sample.

        Args:
            - cursor: MySQL cursor object
            - ir_id (str): interpretation request id of sample

        Returns:
            - sample_id (int): db sample id for given ir_id
        """

        today = datetime.datetime.now().strftime('%Y-%m-%d')

        cursor.execute("SELECT * FROM sample WHERE ir_id='%s'" % (ir_id))
        exists = cursor.fetchone()

        if exists:
            # sample already exist, update with todays date
            cursor.execute(
                "UPDATE sample SET date_last_analysed='%s' WHERE ir_id='%s'" %
                (today, ir_id)
            )

            sample_id = exists[0]
        else:
            # sample doesn't already exist, create new entry
            cursor.execute(
                "INSERT INTO sample (hpoTermList, date_first_analysed,\
                date_last_analysed, ir_id) VALUES ('%s', '%s', '%s', '%s')" %
                ('term', today, today, ir_id)
            )

            # get id of sample inserted
            cursor.execute(
                "SELECT * FROM sample ORDER BY sample_id DESC LIMIT 1"
            )
            sample_id = cursor.fetchone()[0]

        return sample_id


    def save_sample_panel(self, cursor, sample_id, ir_panel):
        """
        Saves samples original panels to sample_panel table

        Args:
            - cursor: MySQL cursor object
            - ir_panel (list): list of tuples of panel(s) used for case

        Returns: None
        """
        cursor.execute(
            "SELECT * FROM sample_panel WHERE sample_id='%s'" % (sample_id)
        )
        panels = cursor.fetchone()
        print(panels)
        if panels:
            # panels already saved
            pass
        else:
            print("saving panels")
            for panel in ir_panel:
                # save each panel and version used, link to sample
                cursor.execute(
                    "INSERT INTO sample_panel (sample_id, name, version)\
                        VALUES\
                    ('%s', '%s', '%s')" %
                    (sample_id, panel[0], panel[2])
                )


    def save_analysis_sample(self, cursor, analysis_id, sample_id):
        """
        Saves to analysis_sample table.
        Stores sample_id and analysis id, creates new analysis_sample_id record
        used to link variants to analysis of sample.

        Args:
            - cursor: MySQL cursor object
            - analysis_id (int): id of analysis
            - sample_id (int): db id of sample

        Returns:
            - analysis_sample_id (int): id of analysis of sample
        """
        query = """
                INSERT INTO analysis_sample
                    (sample_id, analysis_id)
                VALUES
                    (%s, %s)
                """
        data = (sample_id, analysis_id)

        cursor.execute(query, data)

        # get id of inserted row to return
        analysis_sample_id = cursor.lastrowid

        return analysis_sample_id


    def save_analysis_panel(self, cursor, analysis_sample_id, analysis_panels):
        """
        Saves panels and versions used for current analysis of sample

        Args:
            - cursor: MySQL cursor object
            - analysis_sample_id (int): id of analysis of sample
            - analysis_panels (list): list of tuples for each panel and
                version used for reanalysis (panel_name, version)

        Returns: None
        """
        for panel in analysis_panels:
            cursor.execute(
                "INSERT INTO analysis_panel (analysis_sample_id, name, version)\
                    VALUES\
                ('%s', '%s', '%s')" %
                (analysis_sample_id, panel[0], panel[1])
            )


    def save_variant(self, cursor, variant):
        """
        Saves variant to variant table.
        Stores chrom, pos, ref, alt, consequence
        and returns id of new variant row

        Args:
            - variant (dict): dict of variant info

        Returns:
            - variant_id (int): id of newly inserted variant
        """
        data = (variant["chrom"], variant["pos"],
                variant["ref"], variant["alt"],
                variant["consequence"], variant["gene"])
        print(data)
        query_exist = """SELECT * FROM variant WHERE
                            chrom=%s AND pos=%s AND
                            ref=%s AND alt=%s AND
                            consequence=%s AND gene=%s
                    """
        cursor.execute(query_exist, data)

        exists = cursor.fetchone()

        if exists:
            # variant record exists, get variant id
            variant_id = exists[0]
        else:
            # variant record does not exist, insert new record
            query = """
                    INSERT INTO variant
                        (chrom, pos, ref, alt, consequence, gene)
                    VALUES
                        (%s, %s, %s, %s, %s, %s)
                    """
            cursor.execute(query, data)

            # get id of inserted row to return
            variant_id = cursor.lastrowid

        return variant_id


    def save_analysis_variant(self, cursor, analysis_sample_id, variant_id):
        """
        Saves to analysis_variant table.
        Stores analysis_sample id and variant id, links analysis of
        sample to variants present, returns id of variant in the sample
        analysis.

        Args:
            - analysis_sample_id (int): id of sample analysis row,
              returned from save_to_analysis_sample().
            - variant_id (int): id of variant row, returned from
              save_to_variant().

        Returns:
            - analysis_variant_id (int): id of row linking variant in
              sample to current analysis.
        """
        query = """
                INSERT INTO analysis_variant
                    (analysis_sample_id, variant_id)
                VALUES
                    (%s, %s)
                """
        data = (analysis_sample_id, variant_id)
        cursor.execute(query, data)

        analysis_variant_id = cursor.lastrowid

        return analysis_variant_id


    def save_tier(self, cursor, variant):
        """
        Saves tier and/or gets the tier row id

        Args:
            - variant (dict): dict of variant info
        Returns:
            - tier_id (int): id of tier row
        """
        tier = variant["tier"]

        query_exist = 'SELECT * FROM tier WHERE tier="{}"'.format(tier)

        cursor.execute(query_exist)
        exists = cursor.fetchone()

        if exists:
            # variant record exists, get variant id
            tier_id = exists[0]
        else:
            # variant record does not exist, insert new record
            cursor.execute(
                'INSERT INTO tier (tier) VALUES ("{}")'.format(tier)
            )

            # get id of inserted row to return
            tier_id = cursor.lastrowid

        return tier_id


    def save_clinvar(self, cursor, clinvar):
        """
        Saves clinvar annotation to clinvar table

        Args:
            - cursor: MySQL cursor object
            - clinvar (dict): dict of clinvar annotation
        Returns:
            - clinvar_id (int): row id of clinvar annotation
        """

        data = (
            clinvar["clinvar_id"], clinvar["clin_signficance"],
            clinvar["date_last_reviewed"], clinvar["review_status"],
            clinvar["var_type"], clinvar["supporting_submissions"],
            clinvar["chrom"], clinvar["pos"], clinvar["ref"], clinvar["alt"]
        )

        id = (data[0],)

        # check if reccord already exists in table
        query_exist = "SELECT * FROM clinvar WHERE clinvar_id=%s"
        cursor.execute(query_exist, id)

        exists = cursor.fetchone()

        if exists:
            # clinvar record exists, get clinvar id
            clinvar_id = exists[0]
        else:
            # variant record does not exist, insert new record
            query = """
                    INSERT INTO clinvar
                        (clinvar_id, clin_significance,
                        date_last_reviewed, review_status,
                        var_type, supporting_submissions,
                        chrom, pos, ref, alt)
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

            cursor.execute(query, data)

            # get id of inserted row to return
            clinvar_id = data[0]

        return clinvar_id


    def save_hgmd(self, cursor, hgmd):
        """
        Saves HGMD annotation to hgmd table.

        Args:
            - cursor: MySQL cursor object
            - hgmd (dict): dict of hgmd annotation

        Returns:
            - hgmd_id (int): row id of hgmd annotation
        """
        data = (
            hgmd["hgmd_id"], hgmd["rankscore"],
            hgmd["chrom"], int(hgmd["pos"]),
            hgmd["ref"], hgmd["alt"],
            hgmd["dna_change"], hgmd["prot_change"], hgmd["db"],
            hgmd["phenotype"]
        )

        # change None if string to NoneType
        data = [None if x == 'None' else x for x in data]
        data = tuple(data)

        id = (data[0],)

        query_exist = "SELECT * FROM hgmd WHERE hgmd_id=%s"

        cursor.execute(query_exist, id)
        exists = cursor.fetchone()

        if exists:
            # hgmd record exists, get hgmd id
            hgmd_id = exists[0]
            print("hgmd record exists: ", hgmd_id)
        else:
            # variant record does not exist, insert new record

            query = """
                    INSERT INTO hgmd (
                        hgmd_id, rank_score, chrom, pos, ref, alt, dna_change,
                        prot_change, db, phenotype
                    )
                    VALUES
                        (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """

            cursor.execute(query, data)

            # get id of inserted row to return
            hgmd_id = data[0]
            print("new hgmd record: ", hgmd_id)

        return hgmd_id


    def save_pubmed(self, cursor, pubmed):
        """
        Saves pubmed record to pubmed table, returns id to add to pubmed
        list table

        Args:
            - cursor: MySQL cursor object
            - pubmed (dict): dict with pubmed id and title

        Returns:
            - pub_id (int): row id of pubmed enntry
        """

        data = (pubmed["PMID"], pubmed["title"])

        query_exist = """
                        SELECT * FROM pubmed WHERE
                            PMID='%s' AND title='%s'
                        VALUES
                            (%s, %s)
                        """

        cursor.execute(query_exist, data)

        exists = cursor.fetchone()

        if exists:
            # hgmd record exists, get hgmd id
            pubmed_id = exists[0]
        else:
            # variant record does not exist, insert new record
            query = """
                    INSERT INTO pubmed
                        (PMID, title)
                    VALUES
                        (%s, %s)
                    """

            cursor.execute(query, data)

            # get id of inserted row to return
            pubmed_id = cursor.lastrowid

            return pubmed_id


    def save_pubmed_list(self, cursor, pubmed_list):
        """
        Takes list of pubmed ids added for a variant and adds each to
        pubmed list table.

        Args:
            - cursor: MySQL cursor object
            - pubmed_list (list): list of dicts of pubmed ids, ref, alt,
              and associated status

        Returns:
            - pubmed_list_id (int): row id
        """

        # get last list ID and add 1 for current list
        query = """
                SELECT pubmed_list_id from pubmed_list ORDER BY
                pubmed_list_id DESC LIMIT 1;
                """

        pubmed_list_id = cursor.execute(query)
        pubmed_list_id += 1

        for entry in pubmed_list:

            data = (
                pubmed_list_id, entry["pub_id"], entry["associated"],
                entry["ref"], entry["alt"]
            )

            query_save = """
                        INSERT INTO pubmed_list
                            (%s, %s, %s, %s)
                        VALUES
                            (%s, %s, %s, %s)
                        """

            cursor.execute(query_save, data)

        return pubmed_list_id


    def save_variant_annotation(self, cursor, tier_id, clinvar_id, hgmd_id,
                                pubmed_list_id, analysis_variant_id):
        """
        Saves variant annotation to link variant to annotation.

        Args:
            - cursor: MySQL cursor object
            - tier_id (int): table row ID of tier
            - clinvar_id (str): table row ID of entry in ClinVar table
            - hgmd_id (str): table row ID of entry in HGMD table
            - pubmed_list_id (str): table row ID of entry in pubmed list
              table
            - analysis_variant_id (int): table row ID of entry in
              analysis variant table

        Returns: None
        """
        query = """
                INSERT INTO variant_annotation
                    (tier_id, clinvar_id, hgmd_id, pubmed_list_id,
                    analysis_variant_id)
                VALUES
                    (%s, %s, %s, %s, %s)
                """
        data = (
            tier_id, clinvar_id, hgmd_id, pubmed_list_id, analysis_variant_id
        )
        cursor.execute(query, data)


if __name__ == "__main__":

    pass

    # sql = SQLQueries(db_credentials)

    # analysis_run = sql.get_analysis_run(sql.cursor)
    # sql.save_sample(sql.cursor)
    # sql.save_analysis(sql.cursor, analysis_run, sample_id)


    # analysis_run = SQLQueries(db_credentials)
    # save_curr_analysis(db, ir_id, analysis_run, local_clinvar_ver,
    # local_hgmd_ver, variant_list)