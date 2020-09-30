import requests
import base64
import gzip
import glob
import argparse
import os
import csv
import datetime
import config
import json
 
requests.packages.urllib3.disable_warnings()

def getB64():
	""" base64 encodes the credentials for the API """
	message = ":".join([config.username, config.password])
	b64_message = base64.b64encode(message)
	return b64_message


def getToken(b64, log):
	""" 
	Gets authentication token for the WGS SMS service 
	uses a hardcoded string of our base64 encoded credentials
	returns an access_token for authentication on the main API
	"""
	payload = {'grant_type': 'client_credentials'}
	files = []
	headers = {
	  'Authorization': 'Basic {}'.format(b64)
	}
	response = requests.request("POST", config.auth_url, headers=headers, data = payload, files = files)
	payload = response.json()
	updateLog(log, "Requesting Bearer Token from: {}".format(config.auth_url))
	updateLog(log, "\tsuccess: expires_in={}".format(payload['expires_in']))
	return payload['access_token']


def retrieveVCF(token, referal, patient, lsid):
	"""
	requests the return of a previously uploaded VCF
	requires authentication token, referal id, patient id, lab id.
	prints the VCF to STDOUT
	"""
	url = config.sms_url + "/".join([referal, patient, lsid+"?="])
	payload = {}
	headers = {'Authorization': 'Bearer {}'.format(token)}
	response = requests.request("GET", url, headers = headers, data = payload)
	print response.text.encode('utf8')


def uploadVCF(token, payload, referal, patient, lsid, log):
	"""
	Uses am API PUt command to upload a VCF
	requires authentication token, referal id, patient id, lab id.
	Reads VCF into string payload.
	prints API response text to STDOUT
	"""
	url = config.sms_url + "/".join([referal, patient, lsid+"?="])
	headers = {'Content-Type': 'application/x-www-form-urlencoded', 
				'Authorization': 'Bearer {}'.format(token)}
	response = requests.request("PUT", url, headers = headers, data = payload)
	r = json.loads(response.content)
	updateLog(log, response.text.encode('utf8'))
	return r['status']


def uploadCases(token, samples, log):
	""" loop over cases calling uploadVCF() """
	updateLog(log, "Uploading Cases to API")
	responses={}
	for case, details in samples.items():
		status = uploadVCF(
			token, details['payload'], 
			details['ref_id'], details['p_id'], 
			details['lsid'], log)
		responses.setdefault(status, []).append(case)
	return responses		


def load1001(gelcsvs, log):
	"""
	Parses 0..N GEL1001 message (CSV file) into a dictionary
	of dictionaries. First layer is the samples by bnumber
	then under this key there is a dictionary of GEL IDs.
	Referral, Patient and Lims IDs
	"""
	updateLog(log, "Processing {} GEL1001 Messages".format(len(gelcsvs)))
	samples={}
	for x, gelcsv in enumerate(gelcsvs):
		updateLog(log, "\t{}: loading {}".format(str(x+1), gelcsv))
		with open(gelcsv, 'r') as gel:
			csvr = csv.reader(gel)
			for row in csvr:
				if row[0] == "referral_id": 
					continue
				samples[row[8]] = {
					'ref_id': row[0],
					'p_id': row[3],
					'lsid': row[18]
				}
		updateLog(log, "\t\t{} total cases evaluated".format(len(samples.keys())))
	return samples


def processVCF(text, lsid, log):
	"""
	Parse the VCF file content - as list from readlines()
	1) replace Bnumber with the LSID
	2) remove >1300 contigs from the VCF payload.
	3) remove any poor QC variants (!PASS)
	4) remove any loci with multiallelic ALT fields
	return parsed list of lines or 0 if <24 PASS loci
	"""
	parsed = []
	failed = []
	for line in text:
		if line.startswith('##contig'): #remove 100's of CONTIGs from header
			continue
		if line.startswith('#CHROM'): # replace bnumber (VCF sample ID) with LSID
			bits = line.split("\t")
			bits[9] = lsid+'\n'
			line = "\t".join(bits)
		if line.startswith('chr'):
			if not 'PASS' in line: # remove poor quality LOCI
				failed.append(line)
				continue
			fields = line.split('\t')
			ALT = fields[4]
			if len(ALT) > 1: # remove multiallelic loci
				failed.append(line)
				continue
		parsed.append(line)
	
	payload = "".join(parsed)
	if len(failed) > 10: # if less than 24/34 PASS raise an Error
		updateLog(log, '\t\t{} Failed QC after removing {} SNPs - not uploading to API'.format(lsid, str(len(failed))))
		raise ValueError('\tQC failure: {} SNPs omitted - not uploading to API'.format(str(len(failed))))
	else:
		return payload


def saveParsedVCF(case, lsid, body, log):
	date = datetime.date.today().strftime("%d%m%Y")
	newfile=os.path.join(config.log_path, date, "{}_{}.vcf".format(case, lsid))
	updateLog(log, "\t\tSaving parsed VCF: {}".format(newfile))
	with open(newfile, 'w') as newvcf:
		newvcf.write(body)


def prepareVCFs(samples, log):
	"""
	Loop over GEL1001 cases
	1) call readVCF() to load into memory
	2) call processVCF() to QC / update IDs etc
	3) return updated samples dictionary
	"""
	updateLog(log, "Preparing VCF files for upload")
	for case, details in samples.items():
		if details['vcf'] == "na":
			updateLog(log, "\tNo '*snp_genotype.vcf' found for pid: {} - CHECK!!".format(details['p_id']))
		else:
			updateLog(log, "\tProcessing {}: {}".format(case, details['vcf']))
			payload = readVCF(details['vcf'])
			try:
				payload = processVCF(payload, details['lsid'], log)
				saveParsedVCF(case, details['lsid'], payload, log)
				samples[case]['payload'] = payload
			except ValueError as e:
				print e
				samples[case]['payload'] = False
				del(samples[case])
				continue
	return samples


def readVCF(vcf):
	""" read VCF into readlines object """
	vcfh = open(os.path.join(vcf), 'r')
	vcf_list = vcfh.readlines()
	return vcf_list


def findVCFs(samples, path, log):
	"""
	Search supplied directory for VCFs matching Bnumbers in the GEL1001 message(s).
	VCFs are assigned to the sample dictionary if a vcf matches on bnumnber.
	Returns an updated "samples" dictionary with full VCF paths
	"""
	updateLog(log, "Locating VCF files in: {}".format(path))
	pattern = "*snp_genotype.vcf"
	files = glob.glob(os.path.join(path, pattern))
	for case, details in samples.items():
		print case
		hits = [f for f in files if case in f]
		if len(hits) > 0:
			samples[case]['vcf'] = hits[0]
		else:
			samples[case]['vcf'] = "na"
		if samples[case]['vcf'] == "na":
			del(samples[case])

	if len(samples) == 0:
		print "No VCFs found - please check the filepath and try again"
		exit()

	return samples


def initialiseLog():
	"""
	Create log dir under date
	return filehandle to log named <DDMMYYYY>_<HH>_SMS_upload_log.txt
	"""
	date = datetime.date.today().strftime("%d%m%Y")
	date_hm = datetime.datetime.today().strftime("%d%m%Y_%H%M")
	logdir = os.path.join(config.log_path, date)
	if not os.path.exists(logdir):
		os.mkdir(logdir)
	logfile = os.path.join(config.log_path, date, date_hm+"_SMS_upload_log.txt")
	updateLog(logfile, "\n\n==================================")
	updateLog(logfile, "INITIALISED API_SUBMISSION.PY")
	updateLog(logfile, date_hm)
	updateLog(logfile, "==================================")
	return logfile


def updateLog(logpath, message):
	""" writes the message to supplied filepath """
	with open(logpath, 'a') as logh:
		logh.write(message+"\n")


def printSummary(responses, log):
	"""
	Prints a summary to STDOUT showing the number of succesful
	(or not) submissions to the SMS API with a link to the logfile
	"""
	print ["{}: {}".format(r, len(c)) for r, c in responses.items()]
	print "\nProcessing completed... please check:\n\t* {}\n ... for more details\n\n".format(log)


if __name__ == "__main__":
	"""
	This script submits WGS SNP VCFs to the Whole Genome Sequencing
	SNP Matching System (WGS SMS).
	To run this script you need to have the GEL1001 message(s) (CSV)
	containing all of the relevant GEL IDS (referral, patient, lab)
	The user must also supply the path of the VCFs. 
	Authentication tokens will be generated and the VCFs will
	be automatically uploaded.
	"""
	parser = argparse.ArgumentParser()
	parser.add_argument("folder", help="Path of folder containing WGS genotype VCF files",
						type=str)
	parser.add_argument("csv", help="Path of GEL1001 CSV file(s)",
						type=str, nargs="+")
	args = parser.parse_args()

	log = initialiseLog()
	samples = load1001(args.csv, log)
	samples = findVCFs(samples, args.folder, log)
	data = prepareVCFs(samples, log)
	basic = getB64()
	token = getToken(basic, log)
	responses = uploadCases(token, data, log)
	printSummary(responses, log)