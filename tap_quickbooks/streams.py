import hashlib
import re
from datetime import timedelta

import singer
from singer import utils
from singer.utils import strptime_to_utc

import tap_quickbooks.query_builder as query_builder
from tap_quickbooks.client import QuickbooksBadRequestError

LOGGER = singer.get_logger()

DATE_WINDOW_SIZE = 29

class Stream:
    endpoint = '/v3/company/{realm_id}/query'
    key_properties = ['Id']
    replication_method = 'INCREMENTAL'
    # replication keys is LastUpdatedTime, nested under metadata
    replication_keys = ['MetaData']
    additional_where = None
    stream_name = None
    table_name = None

    def __init__(self, client, config, state):
        self.client = client
        self.config = config
        self.state = state


    def sync(self):
        start_position = 1
        max_results = int(self.config.get('max_results', '200'))

        bookmark = singer.get_bookmark(self.state, self.stream_name, 'LastUpdatedTime', self.config.get('start_date'))

        while True:
            query = query_builder.build_query(self.table_name, bookmark, start_position, max_results, additional_where=self.additional_where)

            resp = self.client.get(self.endpoint, params={"query": query,"minorversion": self.client.minor_version}).get('QueryResponse',{})

            results = resp.get(self.table_name, [])
            for rec in results:
                yield rec

            if results:
                self.state = singer.write_bookmark(self.state, self.stream_name, 'LastUpdatedTime', rec.get('MetaData').get('LastUpdatedTime'))
                singer.write_state(self.state)

            if len(results) < max_results:
                break
            start_position += max_results

        singer.write_state(self.state)


class Accounts(Stream):
    stream_name = 'accounts'
    table_name = 'Account'
    additional_where = "Active IN (true, false)"


class Budgets(Stream):
    stream_name = 'budgets'
    table_name = 'Budget'
    additional_where = "Active IN (true, false)"


class Classes(Stream):
    stream_name = 'classes'
    table_name = 'Class'
    additional_where = "Active IN (true, false)"


class CreditMemos(Stream):
    stream_name = 'credit_memos'
    table_name = 'CreditMemo'


class BillPayments(Stream):
    stream_name = 'bill_payments'
    table_name = 'BillPayment'


class SalesReceipts(Stream):
    stream_name = 'sales_receipts'
    table_name = 'SalesReceipt'


class Purchases(Stream):
    stream_name = 'purchases'
    table_name = 'Purchase'


class Payments(Stream):
    stream_name = 'payments'
    table_name = 'Payment'


class PurchaseOrders(Stream):
    stream_name = 'purchase_orders'
    table_name = 'PurchaseOrder'


class PaymentMethods(Stream):
    stream_name = 'payment_methods'
    table_name = 'PaymentMethod'
    additional_where = "Active IN (true, false)"


class JournalEntries(Stream):
    stream_name = 'journal_entries'
    table_name = 'JournalEntry'


class Items(Stream):
    stream_name = 'items'
    table_name = 'Item'
    additional_where = "Active IN (true, false)"


class Invoices(Stream):
    stream_name = 'invoices'
    table_name = 'Invoice'


class Customers(Stream):
    stream_name = 'customers'
    table_name = 'Customer'
    additional_where = "Active IN (true, false)"


class CustomerTypes(Stream):
    stream_name = 'customer_types'
    table_name  = 'CustomerType'


class RefundReceipts(Stream):
    stream_name = 'refund_receipts'
    table_name = 'RefundReceipt'


class Deposits(Stream):
    stream_name = 'deposits'
    table_name = 'Deposit'


class Departments(Stream):
    stream_name = 'departments'
    table_name = 'Department'
    additional_where = "Active IN (true, false)"


class Employees(Stream):
    stream_name = 'employees'
    table_name = 'Employee'
    additional_where = "Active IN (true, false)"


class Estimates(Stream):
    stream_name = 'estimates'
    table_name = 'Estimate'


class Bills(Stream):
    stream_name = 'bills'
    table_name = 'Bill'


class TaxAgencies(Stream):
    stream_name = 'tax_agencies'
    table_name = 'TaxAgency'


class TaxCodes(Stream):
    stream_name = 'tax_codes'
    table_name = 'TaxCode'
    additional_where = "Active IN (true, false)"


class TaxRates(Stream):
    stream_name = 'tax_rates'
    table_name = 'TaxRate'
    additional_where = "Active IN (true, false)"


class Terms(Stream):
    stream_name = 'terms'
    table_name = 'Term'
    additional_where = "Active IN (true, false)"


class TimeActivities(Stream):
    stream_name = 'time_activities'
    table_name = 'TimeActivity'


class Transfers(Stream):
    stream_name = 'transfers'
    table_name = 'Transfer'


class VendorCredits(Stream):
    stream_name = 'vendor_credits'
    table_name = 'VendorCredit'


class Vendors(Stream):
    stream_name = 'vendors'
    table_name = 'Vendor'
    additional_where = "Active IN (true, false)"

class ReportStream(Stream):
    parsed_metadata = {
        'dates': [],
        'data': []
    }
    key_properties = ['ReportDate']
    replication_method = 'INCREMENTAL'
    # replication keys is ReportDate, manually created from data
    replication_keys = ['ReportDate']

    def sync(self):

        is_start_date_used = False
        params = {
            'summarize_column_by': 'Days'
        }

        # Get bookmark for the stream
        start_dttm_str = singer.get_bookmark(self.state, self.stream_name, 'LastUpdatedTime')
        if start_dttm_str is None:
            start_dttm_str = self.config.get('start_date')
            is_start_date_used = True

        # Set start_date and end_date for first date window(30 days) of API calls
        start_dttm = strptime_to_utc(start_dttm_str)
        end_dttm = start_dttm + timedelta(days=DATE_WINDOW_SIZE)
        now_dttm = utils.now()

        # Fetch records for minimum 30 days
        # if bookmark from state file is used and it's less than 30 days away
        # Fetch records for start_date to current date
        # if start_date is used and it'sless than 30 days away
        if end_dttm > now_dttm:
            end_dttm = now_dttm
            if not is_start_date_used:
                start_dttm = end_dttm - timedelta(days=DATE_WINDOW_SIZE)

        # Make a API call in 30 days date window until reach current_time
        while start_dttm < now_dttm:
            self.parsed_metadata = {
                'dates': [],
                'data': []
            }

            start_tm_str = str(start_dttm.date())
            end_tm_str = str(end_dttm.date())

            # Set date window
            params["start_date"] = start_tm_str
            params["end_date"] = end_tm_str

            resp = self.client.get(self.endpoint, params=params)
            self.parse_report_columns(resp.get('Columns', {})) # parse report columns from response's metadata
            self.parse_report_rows(resp.get('Rows', {})) # parse report rows from response's metadata

            reports = self.day_wise_reports() # get reports for every days from parsed metadata
            if reports: # pylint: disable=using-constant-test
                for report in reports:
                    yield report
                self.state = singer.write_bookmark(self.state, self.stream_name, 'LastUpdatedTime', strptime_to_utc(report.get('ReportDate')).isoformat())
                singer.write_state(self.state)

            # Set start_date and end_date of date window for next API call
            start_dttm = end_dttm + timedelta(days=1) # one record is emitted for every day so start from next day
            end_dttm = start_dttm + timedelta(days=DATE_WINDOW_SIZE)

            if end_dttm > now_dttm:
                end_dttm = now_dttm

        singer.write_state(self.state)

    def parse_report_columns(self, pileOfColumns):
        '''
            Restructure columns data in list of dates and update self.parsed_metadata dictionary.
            {
                "dates": ["2021-07-01", "2021-07-02", "2021-07-03"],
                "data": []
            }
            Reference for report metadata: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/report-entities/profitandloss
        '''
        columns = pileOfColumns.get('Column', [])
        for column in columns:
            metadatas = column.get('MetaData', [])
            for metadata in metadatas:
                if metadata['Name'] in ['StartDate']:
                    self.parsed_metadata['dates'].append(metadata['Value'])

    def parse_report_rows(self, pileOfRows):
        '''
            Restructure data from report response on daily basis and update self.parsed_metadata dictionary
            {
                "dates": ["2021-07-01", "2021-07-02", "2021-07-03"],
                "data": [ {
                    "name": "Total Income",
                    "values": ["4.00", "4.00", "4.00", "12.00"]
                }, {
                    "name": "Gross Profit",
                    "values": ["4.00", "4.00", "4.00", "12.00"]
                }, {
                    "name": "Total Expenses",
                    "values": ["1.00", "1.00", "1.00", "3.00"]
                }, {
                    "name": "Net Income",
                    "values": ["3.00", "3.00", "3.00", "9.00"]
                }]
            }
            Reference for report metadata: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/report-entities/profitandloss
        '''

        if isinstance(pileOfRows, list):
            for row in pileOfRows:
                self.parse_report_rows(row)

        else:

            if 'Rows' in pileOfRows.keys():
                self.parse_report_rows(pileOfRows['Rows'])

            if 'Row' in pileOfRows.keys():
                self.parse_report_rows(pileOfRows['Row'])

            if 'Summary' in pileOfRows.keys():
                self.parse_report_rows(pileOfRows['Summary'])

            if 'ColData' in pileOfRows.keys():
                entry_data = dict()
                entry_data['name'] = pileOfRows['ColData'][0]['value']
                vals = []
                for column_value in pileOfRows['ColData'][1:]:
                    vals.append(column_value['value'])
                entry_data['values'] = vals
                self.parsed_metadata['data'].append(entry_data)

    def day_wise_reports(self):
        '''
            Return record for every day formed using output of parse_report_columns and parse_report_rows
        '''
        for index, date in enumerate(self.parsed_metadata['dates']):
            report = dict()
            report['ReportDate'] = date
            report['AccountingMethod'] = 'Accrual'
            report['Details'] = {}

            for data in self.parsed_metadata['data']:
                report['Details'][data['name']] = data['values'][index]

            yield report

class ProfitAndLossReport(ReportStream):
    stream_name = 'profit_loss_report'
    endpoint = '/v3/company/{realm_id}/reports/ProfitAndLoss'

class GeneralLedgerReport(Stream):
    """
        One record per general ledger line, built from the GeneralLedger report.
        Reference: https://developer.intuit.com/app/developer/qbo/docs/api/accounting/all-entities/generalledger
    """
    stream_name = 'general_ledger_report'
    endpoint = '/v3/company/{realm_id}/reports/GeneralLedger'
    key_properties = ['RowKey']
    replication_method = 'INCREMENTAL'
    replication_keys = ['TxnDate']

    # Columns requested from the report; override with config `general_ledger_columns`
    DEFAULT_COLUMNS = 'tx_date,txn_type,doc_num,name,memo,split_acc,debt_amt,credit_amt,rbal_nat_amount'
    # Window size (days) of every API call; a window is halved when QuickBooks rejects it as too large
    GL_WINDOW_SIZE = 31

    # report column key -> record field
    COLUMN_FIELDS = {
        'tx_date': 'TxnDate',
        'txn_type': 'TxnType',
        'doc_num': 'DocNumber',
        'name': 'Name',
        'memo': 'Memo',
        'split_acc': 'SplitAccount',
        'rbal_nat_amount': 'Balance',
        'debt_amt': 'Debit',
        'credit_amt': 'Credit',
    }
    AMOUNT_COLUMNS = ('rbal_nat_amount', 'debt_amt', 'credit_amt')
    # Columns the record cannot be built without
    REQUIRED_COLUMNS = ('tx_date', 'txn_type', 'debt_amt', 'credit_amt')

    def sync(self):
        bookmark = singer.get_bookmark(self.state, self.stream_name, 'LastUpdatedTime')
        # Backdated entries (e.g. payroll) can land in closed days, so re-read a lookback window
        lookback = int(self.config.get('general_ledger_lookback_days', 30))
        if bookmark:
            start_dttm = strptime_to_utc(bookmark) - timedelta(days=lookback)
            start_dttm = max(start_dttm, strptime_to_utc(self.config.get('start_date')))
        else:
            start_dttm = strptime_to_utc(self.config.get('start_date'))

        today = utils.now().date()
        start = start_dttm.date()

        while start <= today:
            end = min(start + timedelta(days=self.GL_WINDOW_SIZE - 1), today)
            for rec in self.sync_window(start, end):
                yield rec

            self.state = singer.write_bookmark(self.state, self.stream_name, 'LastUpdatedTime',
                                               strptime_to_utc(str(end)).isoformat())
            singer.write_state(self.state)
            start = end + timedelta(days=1)

        singer.write_state(self.state)

    def sync_window(self, start, end):
        """Fetch one date window, halving it when QuickBooks rejects it as too large."""
        params = {
            'start_date': str(start),
            'end_date': str(end),
            'columns': self.config.get('general_ledger_columns', self.DEFAULT_COLUMNS),
            'sort_by': 'tx_date',
            'sort_order': 'ascend',
            'accounting_method': self.config.get('general_ledger_accounting_method', 'Accrual'),
            'minorversion': self.client.minor_version,
        }
        try:
            resp = self.client.get(self.endpoint, params=params)
        except QuickbooksBadRequestError:
            if start >= end:
                raise
            mid = start + (end - start) // 2
            LOGGER.warning('GeneralLedger window %s..%s rejected, splitting at %s', start, end, mid)
            yield from self.sync_window(start, mid)
            yield from self.sync_window(mid + timedelta(days=1), end)
            return

        yield from self.parse_report(resp)

    def parse_report(self, resp):
        """Flatten the nested sections of a GeneralLedger response into one record per line."""
        col_keys = []
        for column in resp.get('Columns', {}).get('Column', []):
            key = None
            for meta in column.get('MetaData', []):
                if meta.get('Name') == 'ColKey':
                    key = meta.get('Value')
            col_keys.append(key)

        # QuickBooks silently ignores unknown columns, which would emit empty lines; fail loudly instead
        if col_keys:
            missing = [c for c in self.REQUIRED_COLUMNS if c not in col_keys]
            if missing:
                raise Exception('GeneralLedger report is missing required columns {}; check '
                                'general_ledger_columns (got {})'.format(missing, col_keys))

        records = []
        for account_id, account_name, cols in self.walk_rows(resp.get('Rows', {}), None, None):
            rec = self.build_record(col_keys, cols, account_id, account_name)
            if rec is not None:
                records.append(rec)

        # Key on the line's identity, not its content, so an edited or backdated line overwrites its
        # old row. Lines of one transaction share a date, hence a window. Lines of one (transaction,
        # account) are ranked by content, not by the order QuickBooks returns them, which varies with
        # the window size. Without a transaction id fall back to content.
        groups = {}
        for rec in records:
            if rec.get('TxnId'):
                fields = ('TxnType', 'TxnId', 'AccountId')
            else:
                fields = ('TxnType', 'TxnDate', 'DocNumber', 'AccountId', 'Name', 'Memo',
                          'SplitAccount', 'Debit', 'Credit')
            base = '|'.join(str(rec.get(k)) for k in fields)
            groups.setdefault(base, []).append(rec)
        for base, lines in groups.items():
            lines.sort(key=lambda r: tuple(str(r.get(k) or '') for k in (
                'Memo', 'Debit', 'Credit', 'Name', 'SplitAccount', 'DocNumber', 'TxnDate')))
            for rank, rec in enumerate(lines, 1):
                rec['RowKey'] = hashlib.sha1('{}|{}'.format(base, rank).encode()).hexdigest()
        yield from records

    def walk_rows(self, node, account_id, account_name):
        """Yield (account_id, account_name, ColData) for every data row, tracking the enclosing account section."""
        for row in node.get('Row', []):
            if row.get('type') == 'Section' or 'Rows' in row:
                header = row.get('Header', {}).get('ColData', [])
                if header:
                    # A section without an id (e.g. a parent account or "Not Specified") is not a real account
                    inner_id, inner_name = header[0].get('id'), header[0].get('value')
                else:
                    inner_id, inner_name = account_id, account_name
                yield from self.walk_rows(row.get('Rows', {}), inner_id, inner_name)
            elif row.get('ColData') and row.get('type', 'Data') == 'Data':
                yield account_id, account_name, row['ColData']

    def build_record(self, col_keys, cols, account_id, account_name):
        values = {}
        ids = {}
        for key, col in zip(col_keys, cols):
            values[key] = col.get('value')
            ids[key] = col.get('id')

        txn_date = values.get('tx_date')
        # Skip "Beginning Balance" and any other non-transaction row
        if not txn_date or not re.match(r'^\d{4}-\d{2}-\d{2}$', txn_date):
            return None

        rec = {
            'AccountId': account_id,
            'AccountName': account_name,
            'TxnId': ids.get('txn_type') or ids.get('tx_date') or ids.get('doc_num'),
        }
        for key, field in self.COLUMN_FIELDS.items():
            if key in values:
                rec[field] = self.to_amount(values[key]) if key in self.AMOUNT_COLUMNS else (values[key] or None)

        # QuickBooks leaves the unused side blank
        rec['Debit'] = rec.get('Debit') or 0.0
        rec['Credit'] = rec.get('Credit') or 0.0
        return rec

    @staticmethod
    def to_amount(value):
        if value in (None, ''):
            return None
        try:
            return float(str(value).replace(',', ''))
        except ValueError:
            return None


class DeletedObjects(Stream):
    endpoint = '/v3/company/{realm_id}/cdc'
    stream_name = 'deleted_objects'
    table_name = 'DeletedObjects'
    key_properties = ['Id', 'Type']
    max_date = None
    is_deleted_object_found = False

    # Change tracking is not supported for TimeActivities, TaxAgencies, TaxCodes and TaxRates
    # Reference: https://developer.intuit.com/app/developer/qbo/docs/develop/explore-the-quickbooks-online-api/change-data-capture
    deleted_entities = ['Account', 'BillPayment', 'Bill', 'Budget', 'Class', 'CreditMemo',
                        'Customer', 'Department', 'Deposit', 'Employee', 'Estimate', 'Invoice',
                        'Item', 'JournalEntry', 'PaymentMethod', 'Payment', 'PurchaseOrder', 'Purchase',
                        'RefundReceipt', 'SalesReceipt', 'Term', 'Transfer', 'VendorCredit', 'Vendor']

    def sync(self):

        bookmark = singer.get_bookmark(self.state, self.stream_name, 'LastUpdatedTime', self.config.get('start_date'))
        self.max_date = bookmark
        params = {
            'entities': ','.join(self.deleted_entities),
            'changedSince': bookmark
        }

        # Get change tracking for all the entities in single call
        resp = self.client.get(self.endpoint, params=params).get('CDCResponse',[{}])[0].get('QueryResponse', [{}])

        # Calculate number of objects found in response
        total_objects = 0
        for entities in resp:
            for entity, values in entities.items():
                if isinstance(values, list):
                    total_objects += len(values)

        # Change tracking API return maximum 1000 object changes.
        # So if objects are not less than 1000 then make individual call for every entity
        # Reference: https://developer.intuit.com/app/developer/qbo/docs/develop/explore-the-quickbooks-online-api/change-data-capture

        if total_objects < 1000:
            yield from self.parse_data_and_write(resp)
        else:
            for entity in self.deleted_entities:
                params = {
                    'entities': entity,
                    'changedSince': bookmark
                }
                resp = self.client.get(self.endpoint, params=params).get('CDCResponse',[{}])[0].get('QueryResponse', [{}])
                yield from self.parse_data_and_write(resp)

        # Write bookmark if any deleted object found
        if self.is_deleted_object_found:
            self.state = singer.write_bookmark(self.state, self.stream_name, 'LastUpdatedTime', self.max_date)

        singer.write_state(self.state)

    def parse_data_and_write(self, response):
        '''
            Parse change tracking response and return every deleted entity
        '''
        for entities in response:
            for entity, values in entities.items():
                if isinstance(values, list):
                    for rec in values:
                        if rec.get('status', None) == 'Deleted':
                            self.is_deleted_object_found = True
                            rec['Type'] = entity
                            self.max_date = max(self.max_date, rec.get('MetaData').get('LastUpdatedTime'))
                            yield rec


STREAM_OBJECTS = {
    "accounts": Accounts,
    "bill_payments": BillPayments,
    "bills": Bills,
    "budgets": Budgets,
    "classes": Classes,
    "credit_memos": CreditMemos,
    "customers": Customers,
    "customer_types": CustomerTypes,
    "departments": Departments,
    "deposits": Deposits,
    "employees": Employees,
    "estimates": Estimates,
    "invoices": Invoices,
    "items": Items,
    "journal_entries": JournalEntries,
    "payment_methods": PaymentMethods,
    "payments": Payments,
    "purchase_orders": PurchaseOrders,
    "purchases": Purchases,
    "refund_receipts": RefundReceipts,
    "sales_receipts": SalesReceipts,
    "tax_agencies": TaxAgencies,
    "tax_codes": TaxCodes,
    "tax_rates": TaxRates,
    "terms": Terms,
    "time_activities": TimeActivities,
    "transfers": Transfers,
    "vendor_credits": VendorCredits,
    "vendors": Vendors,
    "profit_loss_report": ProfitAndLossReport,
    "general_ledger_report": GeneralLedgerReport,
    "deleted_objects": DeletedObjects
}
