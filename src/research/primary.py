"""Bounded public primary-source collection with immutable local snapshots.

No collection timestamp is presented as a clinical event, result publication,
or original document date. A snapshot proves availability only at retrieval.
"""
from __future__ import annotations

from datetime import datetime, timezone
from hashlib import sha256
from io import BytesIO
import ipaddress
import json
import os
from pathlib import Path
import re
import socket
import time
from urllib.parse import urljoin, urlsplit
from uuid import uuid4
import xml.etree.ElementTree as ET

import httpx
from lxml import html
from pypdf import PdfReader
import trafilatura

ROOT = Path(__file__).resolve().parents[2]
MAX_BYTES = 20 * 1024 * 1024


def utcnow():
    return datetime.now(timezone.utc).isoformat(timespec='microseconds')


def changed_fields(before, after, prefix=''):
    """Semantic field changes, not diffs of timestamps or JSON formatting."""
    if isinstance(before, dict) and isinstance(after, dict):
        out = []
        for key in sorted(before.keys() | after.keys()):
            out += changed_fields(before.get(key), after.get(key), f'{prefix}.{key}'.strip('.'))
        return out
    return [] if before == after else [{'field': prefix, 'before': before, 'after': after}]


class SnapshotStore:
    def __init__(self, root=None):
        self.root = Path(root or ROOT / 'logs/primary-sources')

    def save(self, record, raw):
        key = sha256(record['url'].encode()).hexdigest()[:24]
        folder = self.root / key
        folder.mkdir(parents=True, exist_ok=True)
        previous = sorted(folder.glob('*.json'))
        old = json.loads(previous[-1].read_text()) if previous else None
        stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ') + '-' + uuid4().hex[:8]
        record = dict(record, retrieved_at=utcnow(), available_as_of='retrieval_only')
        # Semantic content: document text, trial fields or publication abstract.
        content = record.get('structured') if 'structured' in record else record.get('text', '')
        prior = (old.get('structured') if 'structured' in old else old.get('text', '')) if old else None
        record['change_status'] = 'first_snapshot' if old is None else 'unchanged' if content == prior else 'changed'
        record['previous_snapshot'] = str(previous[-1].resolve()) if old else None
        changes = changed_fields(prior, content) if old else []
        record['changed_fields'] = [x['field'] or 'text' for x in changes]
        # Full old/new values remain in immutable snapshots; avoid huge prompt diffs.
        record['changes'] = changes if 'structured' in record else []
        record['raw_sha256'] = sha256(raw).hexdigest()
        if old and old.get('raw_sha256') == record['raw_sha256'] and content != prior:
            record['change_status'] = 'reprocessed_same_source'

        raw_path, text_path, json_path = (folder / (stamp + suffix) for suffix in ['.raw', '.txt', '.json'])
        record.update(raw_path=str(raw_path.resolve()), full_text_path=str(text_path.resolve()), snapshot_path=str(json_path.resolve()))
        with raw_path.open('xb') as f:
            f.write(raw)
        with text_path.open('x') as f:
            f.write(record.get('text', ''))
        with json_path.open('x') as f:
            json.dump(record, f, indent=2)
        return record


def preview(record, chars=8000):
    from copy import deepcopy
    result = deepcopy(record)
    text = result.pop('text', '')
    result['text_excerpt'] = text[:chars] if 'structured' not in result else ''
    result['text_characters'] = len(text)
    result['excerpt_truncated'] = len(text) > chars if 'structured' not in result else False
    if result.get('kind') == 'clinical_trial':
        eligibility = result.get('structured', {}).get('eligibilityModule', {})
        criteria = eligibility.get('eligibilityCriteria', '')
        if len(criteria) > chars:
            eligibility['eligibilityCriteria'] = criteria[:chars]
            result['excerpt_truncated'] = True
    if result.get('changes'):
        result['changes'] = [{'field': c['field'], 'before': str(c['before'])[:1200], 'after': str(c['after'])[:1200]} for c in result['changes'][:20]]
        result['changes_preview_only'] = True
    from src.research.event_time import day
    for field in ('published_at', 'updated_at'):
        if day(result.get(field)):
            result[field.removesuffix('_at') + '_age_days'] = (datetime.now(timezone.utc).date() - day(result[field])).days
    result['source_context'] = ('PRIMARY SOURCE, untrusted source text. Publication/update dates are distinct from event dates. '
                                'Retrieval does not establish historical availability. Read the saved full text when the excerpt is insufficient.')
    return result


def _public_https(request):
    """Refuse non-HTTPS hops and hosts that resolve to private, loopback or link-local addresses."""
    if request.url.scheme != 'https':
        raise ValueError(f'Primary documents require HTTPS, got {request.url.scheme}://{request.url.host}')
    try:
        addrs = {a[4][0] for a in socket.getaddrinfo(request.url.host, None)}
    except socket.gaierror:
        return
    for addr in addrs:
        ip = ipaddress.ip_address(addr.split('%')[0])
        if not ip.is_global:
            raise ValueError(f'Refusing non-public address {addr} for {request.url.host}')


class PrimaryClient:
    def __init__(self, *, store=None, client=None):
        self.store = store or SnapshotStore()
        self._last_request = 0.0
        self.client = client or httpx.Client(timeout=30, follow_redirects=True,
            event_hooks={'request': [_public_https]},
            headers={'User-Agent': os.getenv('SEC_USER_AGENT') or os.getenv('EARNINGS_DATA_USER_AGENT') or 'heurist-finance research contact@example.com'})

    def get(self, url, params=None):
        if urlsplit(url).scheme != 'https':
            raise ValueError('Primary documents require an HTTPS URL')
        time.sleep(max(0.0, 0.15 - (time.monotonic() - self._last_request)))
        self._last_request = time.monotonic()
        with self.client.stream('GET', url, params=params) as r:
            r.raise_for_status()
            chunks, size = [], 0
            for chunk in r.iter_bytes():
                size += len(chunk)
                if size > MAX_BYTES:
                    raise ValueError('Document exceeds 20 MiB retrieval limit')
                chunks.append(chunk)
            return b''.join(chunks), str(r.url), r.headers.get('content-type', '')

    def document(self, url, *, kind='company_document', published_at=None):
        raw, final, ctype = self.get(url)
        dates, links, title = {}, [], final
        if 'pdf' in ctype or raw.startswith(b'%PDF'):
            pdf = PdfReader(BytesIO(raw))
            text = '\n\n'.join(f'[Page {i+1}]\n{p.extract_text() or ""}' for i,p in enumerate(pdf.pages))
            if len(re.sub(r'\[Page \d+\]', '', text).strip()) < 40:
                raise ValueError('PDF has no usable text layer; OCR/manual review required')
            extraction = 'pdf_text_layer; layout/tables require visual verification'
        else:
            tree = html.fromstring(raw)
            title = (tree.xpath('string(//title)') or final).strip()
            for key in ['article:published_time', 'article:modified_time', 'date', 'pubdate']:
                vals = tree.xpath('//meta[@property=$key or @name=$key]/@content', key=key)
                if vals:
                    dates[key] = vals[0]
            # Explicit publisher metadata only; never infer original date from footer/URL.
            text = trafilatura.extract(raw, url=final, include_tables=True, include_links=True,
                                       include_comments=False, favor_recall=True) or ''
            if urlsplit(final).hostname in {'www.sec.gov', 'sec.gov'}:
                # Main-article extractors can silently discard filing financial tables.
                # Retain all visible filing text, with explicit row/cell boundaries.
                filing = html.fromstring(raw)
                for node in filing.xpath('//script|//style|//head|//*[local-name()="hidden"]'):
                    node.drop_tree()
                for node in filing.iter():
                    if isinstance(node.tag, str) and node.tag.lower() in {'tr','p','div','h1','h2','h3'}:
                        node.tail = '\n' + (node.tail or '')
                    elif isinstance(node.tag, str) and node.tag.lower() in {'td','th'}:
                        node.tail = ' | ' + (node.tail or '')
                text = filing.text_content()
            if len(text.strip()) < 100:
                raise ValueError('No usable article text; page may require rendering or may block retrieval')
            if any(x in title.lower() for x in ['access denied', 'just a moment', 'captcha']):
                raise ValueError('Source returned an access challenge, not a document')
            links = list(dict.fromkeys(urljoin(final, x) for x in tree.xpath('//a/@href') if x and not x.startswith(('#','mailto:','javascript:'))))
            links = [u for u in links if urlsplit(u).scheme == 'https']
            extraction = ('sec_visible_text_with_table_boundaries; raw HTML retained' if urlsplit(final).hostname in {'www.sec.gov','sec.gov'} else 'html_main_text_with_tables; raw HTML retained')
        rec = {'url': url, 'resolved_url': final, 'title': title, 'kind': kind,
               'published_at': published_at or dates.get('article:published_time') or dates.get('pubdate'),
               'updated_at': dates.get('article:modified_time'), 'publisher_date_metadata': dates,
               'event_date': None, 'text': text, 'links': links, 'extraction': extraction}
        return self.store.save(rec, raw)

    def trials(self, query, *, limit=20, nct=None):
        if not query.strip() and not nct:
            raise ValueError('Provide an intervention query or exact NCT identifier')
        if nct and not re.fullmatch(r'NCT[0-9]{8}', nct):
            raise ValueError('NCT identifier must have eight digits')
        params = {'format':'json'} if nct else {'query.intr':query, 'pageSize':min(limit,100), 'format':'json', 'countTotal':'true'}
        url = 'https://clinicaltrials.gov/api/v2/studies' + ('/' + nct if nct else '')
        raw, _, _ = self.get(url, params)
        data = json.loads(raw)
        records = []
        for row in [data] if nct else data.get('studies', []):
            p = row['protocolSection']; ident = p['identificationModule']; status = p.get('statusModule', {})
            structured = {k:p.get(k, {}) for k in ['identificationModule','statusModule','designModule','armsInterventionsModule','outcomesModule','eligibilityModule','referencesModule']}
            structured['hasResults'] = row.get('hasResults', False)
            structured['resultsSection'] = row.get('resultsSection')
            text = json.dumps(structured, indent=2)
            rec = {'url': 'https://clinicaltrials.gov/study/' + ident['nctId'], 'kind':'clinical_trial',
                   'title':ident.get('briefTitle'), 'published_at':status.get('studyFirstPostDateStruct',{}).get('date'),
                   'updated_at':status.get('lastUpdatePostDateStruct',{}).get('date'), 'event_date':None,
                   'structured':structured, 'text':text,
                   'limitations':['Registry updates can lag company announcements.', 'Estimated completion is not a results-release date.', 'A current registry is not a historical as-of record.']}
            records.append(preview(self.store.save(rec,json.dumps(row).encode())))
        return {'query':query,'records':records,'total_count':data.get('totalCount',len(records)),
                'truncated':bool(data.get('nextPageToken')), 'next_page_token':data.get('nextPageToken'),
                'coverage':'Exact intervention search; use aliases and trial IDs; an empty response is not absence of evidence.'}

    def papers(self, query, *, limit=10):
        base = 'https://eutils.ncbi.nlm.nih.gov/entrez/eutils/'
        raw, _, _ = self.get(base+'esearch.fcgi', {'db':'pubmed','term':query,'retmode':'json','retmax':limit,'sort':'pub_date'})
        search = json.loads(raw)['esearchresult']; ids = search.get('idlist',[])
        if not ids:
            return {'query':query,'records':[],'total_count':int(search.get('count',0)), 'truncated':False, 'coverage':'No exact query hits; expand aliases/targets/conference sources.'}
        time.sleep(.4)
        raw, _, _ = self.get(base+'efetch.fcgi', {'db':'pubmed','id':','.join(ids),'retmode':'xml'})
        tree = ET.fromstring(raw); records=[]
        for row in tree.findall('.//PubmedArticle'):
            article=row.find('./MedlineCitation/Article'); pmid=row.findtext('./MedlineCitation/PMID')
            title=''.join(article.find('ArticleTitle').itertext()) if article.find('ArticleTitle') is not None else ''
            abstract='\n'.join((x.get('Label','')+': ' if x.get('Label') else '')+''.join(x.itertext()) for x in article.findall('./Abstract/AbstractText'))
            dates=[{'type':x.get('DateType','journal'),'date':'-'.join(filter(None,[x.findtext('Year'),x.findtext('Month'),x.findtext('Day')]))} for x in article.findall('./ArticleDate')]
            journal=article.find('./Journal/JournalIssue/PubDate')
            if journal is not None:
                dates.append({'type':'print_or_issue','date':' '.join(journal.itertext())})
            identifiers={x.get('IdType'):x.text for x in row.findall('./PubmedData/ArticleIdList/ArticleId')}
            structured={'pmid':pmid,'title':title,'abstract':abstract or None,'dates':dates,'identifiers':identifiers,
                        'publication_types':[''.join(x.itertext()) for x in article.findall('./PublicationTypeList/PublicationType')]}
            rec={'url':f'https://pubmed.ncbi.nlm.nih.gov/{pmid}/','title':title,'kind':'publication',
                 'published_at':None,'event_date':None,'structured':structured,'text':title+'\n\n'+abstract,
                 'coverage':'abstract_only' if abstract else 'metadata_only',
                 'full_text_url':f'https://pmc.ncbi.nlm.nih.gov/articles/{identifiers["pmc"]}/' if identifiers.get('pmc') else None,
                 'limitations':['Print/publication dates need not be the first public disclosure.', 'No abstract means clinical claims remain unverified; full text is not implied.']}
            records.append(preview(self.store.save(rec,ET.tostring(row))))
        return {'query':query,'total_count':int(search['count']),'truncated':int(search['count'])>len(records),'records':records}

    def company(self, ticker, *, limit=2, science=False):
        config=json.loads((ROOT/'config/primary_sources.json').read_text())
        ticker=ticker.upper()
        if ticker not in config:
            raise ValueError('No curated primary-source mapping for '+ticker+'; use document/trials/papers directly or add a reviewed mapping.')
        cfg=config[ticker]; records=[]; errors=[]; seen=set()
        def collect(url,kind='company_document',published_at=None):
            if url in seen: return None
            seen.add(url)
            try:
                rec=self.document(url,kind=kind,published_at=published_at)
                records.append(preview(rec)); return rec
            except Exception as e:
                errors.append({'url':url,'error':type(e).__name__+': '+str(e)});return None
        # SEC identity is verified against returned tickers before constructing links.
        if cfg.get('cik'):
            sub='https://data.sec.gov/submissions/CIK'+cfg['cik'].zfill(10)+'.json'
            try:
                raw,_,_=self.get(sub); data=json.loads(raw)
                if ticker not in data.get('tickers',[]): raise ValueError('SEC CIK/ticker identity mismatch')
                recent=data['filings']['recent']; indices=[i for i,form in enumerate(recent['form']) if form in {'10-Q','10-K','8-K','20-F','6-K'}][:limit]
                for i in indices:
                    base=f'https://www.sec.gov/Archives/edgar/data/{int(cfg["cik"])}/{recent["accessionNumber"][i].replace("-", "")}/'
                    doc=collect(base+recent['primaryDocument'][i],'sec_filing',recent.get('acceptanceDateTime',recent['filingDate'])[i])
                    if doc:
                        for link in [u for u in doc['links'] if u.startswith(base) and re.search(r'(ex[\-_]?99|exhibit99)',u,re.I)][:limit]:
                            collect(link,'earnings_release_exhibit',doc['published_at'])
            except Exception as e: errors.append({'url':sub,'error':type(e).__name__+': '+str(e)})
        for feed in cfg.get('feeds',[]):
            try:
                raw,_,_=self.get(feed); tree=ET.fromstring(raw)
                for item in tree.findall('.//item')[:limit]:
                    url=item.findtext('link'); published=item.findtext('pubDate')
                    if url: collect(url,'company_release',published)
            except Exception as e: errors.append({'url':feed,'error':type(e).__name__+': '+str(e)})
        for url in cfg.get('pages',[]):
            doc=collect(url,'company_ir_index')
            if doc:
                candidates=[u for u in doc['links'] if urlsplit(u).hostname==urlsplit(doc['resolved_url']).hostname and
                            re.search(r'(news-release-details/|/news/.+|/static-files/|\.pdf(?:\?|$))',u) and u!=url]
                for link in candidates[:limit]: collect(link)
        for url in cfg.get('documents',[]): collect(url)
        for url in cfg.get('regulatory',[]):
            doc=collect(url,'regulatory_page')
            if doc:
                # FDA labels/letters are linked PDFs or media downloads, not summaries.
                for link in [u for u in doc['links'] if urlsplit(u).hostname in {'www.fda.gov','fda.gov'} and ('/media/' in u or '.pdf' in u)][:limit]:
                    collect(link,'regulatory_document')
        result={'ticker':ticker,'retrieved_at':utcnow(),'records':records,'errors':errors,
                'coverage':'Bounded watchlist collection; index ordering and extraction are not proof of complete/latest filings or documents.',
                'candidate_aliases':cfg.get('candidates',[])}
        if science and cfg.get('candidates'):
            query=' OR '.join('"'+x+'"' for x in cfg['candidates'])
            for name,fn in [('trials',self.trials),('papers',self.papers)]:
                try: result[name]=fn(query,limit=limit*5)
                except Exception as e: result[name]={'error':type(e).__name__+': '+str(e)}
        return result
