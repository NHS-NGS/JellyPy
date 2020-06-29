import datetime
import os
import sqlite3

# mock data to test
gel_sample_id = "55904-12"
hpo_terms = [{'termPresence': 'no', 'term': 'HP:0000009'}, {'termPresence': 'no', 'term': 'HP:0000496'}]
local_clinvar_ver = "20200407"
local_hgmd_ver = "2020.1" 
variant_list = [{'position': 42752767, 'chromosome': '15', 'ref': 'T', 'alt': 'C', 'tier': 'TIER2', 'type': None}, {'position': 32519435, 'chromosome': '6', 'ref': 'C', 'alt': 'T', 'tier': 'TIER3', 'type': 'missense_variant'}, {'position': 56996321, 'chromosome': '12', 'ref': 'C', 'alt': 'G', 'tier': 'TIER3', 'type': '2KB_upstream_variant'}, {'position': 56621391, 'chromosome': '19', 'ref': 'CAGA', 'alt': 'C', 'tier': 'TIER3', 'type': 'inframe_deletion'}, {'position': 61908223, 'chromosome': '11', 'ref': 'T', 'alt': 'C', 'tier': 'TIER3', 'type': 'missense_variant'}, {'position': 142402820, 'chromosome': '6', 'ref': 'T', 'alt': 'C', 'tier': 'TIER3', 'type': 'missense_variant'}, {'position': 151086821, 'chromosome': '7', 'ref': 'C', 'alt': 'G', 'tier': 'TIER3', 'type': '2KB_upstream_variant'}, {'position': 42752767, 'chromosome': '15', 'ref': 'T', 'alt': 'C', 'tier': 'TIER3', 'type': 'missense_variant'}, {'position': 104641647, 'chromosome': '10', 'ref': 'G', 'alt': 'T', 'tier': 'TIER3', 'type': 'missense_variant'}]


def connect():
    """
    Open connection to database

    Args: None

    Returns:
        - conn ():
        - curs ():
    """
    db = os.path.join(os.path.dirname(__file__), "../data/100k_reanalysis.db")
    conn = sqlite3.connect(db, isolation_level=None)
    curs = conn.cursor()
    
    return conn, curs


def new_analysis_run():
    """
    Check last analysis_run value and returns =+1

    Args: None

    Returns:
        - analysis run (int): number for new analysis run
    """
    last_run = curs.execute("SELECT MAX(analysis_run) FROM analysis").fetchone()[0]

    if last_run:
        # get last run and increase by 1
        analysis_run = int(last_run) + 1
    else:
        # empty table, start at 1
        analysis_run = 1
    
    print(analysis_run)

    return analysis_run
    

def check_sample(conn, curs, gel_sample_id):
    """
    Checks if gel sample ID exists in db already, if it does just update
    date last analysed, if not add as new record

    Args:
        - conn ():
        - curs ():
        - sample_id (str):
    
    Returns: None 
    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    curs.execute("SELECT * FROM sample WHERE gel_sample=?", (gel_sample_id,))
    
    if curs.fetchone():
        # sample already exist
        print("existing sample")
        
        curs.execute("UPDATE sample SET date_last_analysed=? WHERE gel_sample=?", 
            (today, gel_sample_id))
        conn.commit()

    else:
        # sample doesn't already exist
        curs.execute("INSERT INTO sample (hpo_terms, date_first_analysed,\
                                        date_last_analysed, gel_sample)\
                    VALUES (?, ?, ?, ?)", ('term', today, today, gel_sample_id))
        conn.commit()


def save_curr_analysis(conn, curs, gel_sample_id, analysis_run, local_clinvar_ver, local_hgmd_ver, variant_list):
    """
    Create new analysis for sample, store variants and annotation

    Args:
        - conn():
        - curs():

    """
    today = datetime.datetime.now().strftime('%Y-%m-%d')

    # get the sample_id for current gel_sample_id
    curs.execute("SELECT sample_id FROM sample WHERE gel_sample=?",
        (gel_sample_id,)
    )
    sample_id = curs.fetchone()[0]

    # add new analysis
    query = """
            INSERT INTO analysis
                (sample_id, analysis_date, clinvar_ver, hgmd_ver, analysis_run)
            VALUES
                (?, ?, ?, ?, ?)
            """
    data = [sample_id, today, local_clinvar_ver, local_hgmd_ver, analysis_run]
    curs.execute(query, data)

    analysis_id = curs.lastrowid

    # loop over list of variants and add to db
    for var in variant_list:

        curs.execute("""SELECT * FROM variant WHERE
                        (position=? AND chrom=? AND ref=? AND alt=?)""",                       
                    (var['position'], var['chromosome'],
                    var['ref'], var['alt'])
                    )
        
        exist_var = curs.fetchone()

        if exist_var:
            # variant already exists, link to variant
            print("found variant")
            variant_id = exist_var[0]

        else:
            print("new variant")    
            curs.execute("""INSERT INTO variant 
                            (build, chrom, position, ref, alt, type) 
                            VALUES (?, ?, ?, ?, ?, ?)""",
                            (
                                '38', var['chromosome'], var['position'], 
                                var['ref'], var['alt'], var['type']
                            )
                        )
            variant_id = curs.lastrowid

        # link current analysis to variants
        curs.execute("""INSERT INTO analysis_variant
                        (analysis_id, variant_id)
                        VALUES (?, ?)""",
                        (analysis_id, variant_id)
                    )


    




if __name__ == "__main__":

    conn, curs = connect()
    analysis_run = new_analysis_run()
    check_sample(conn, curs, gel_sample_id)
    save_curr_analysis(conn, curs, gel_sample_id, analysis_run, local_clinvar_ver, local_hgmd_ver, variant_list)