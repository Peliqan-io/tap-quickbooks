import datetime
import unittest
import tap_quickbooks.streams as streams


class TestReportsParser(unittest.TestCase):

    def test_day_wise_reports(self):
        """
        Test that day wise reports are generated from formatted parsed_metadata
        """
        reports = streams.ReportStream("", "", "")
        reports.parsed_metadata = {
            "dates": ["2021-07-01", "2021-07-02", "2021-07-03"],
            "data": [
                {
                    "name": "Total Income",
                    "values": ["4.00", "5.00", "6.00", "15.00"]
                }, {
                    "name": "Gross Profit",
                    "values": ["3.00", "4.00", "5.00", "12.00"]
                }
            ]
        }

        expected_records = [
            {
                "ReportDate": "2021-07-01",
                "AccountingMethod": "Accrual",
                "Details": {"Total Income": "4.00", "Gross Profit": "3.00"}
            },
            {
                "ReportDate": "2021-07-02",
                "AccountingMethod": "Accrual",
                "Details": {"Total Income": "5.00", "Gross Profit": "4.00"}
            },
            {
                "ReportDate": "2021-07-03",
                "AccountingMethod": "Accrual",
                "Details": {"Total Income": "6.00", "Gross Profit": "5.00"}
            }
        ]

        records = list(reports.day_wise_reports())
        self.assertListEqual(expected_records, records)

    def test_report_parser(self):
        """
        Test that metadata returned from report API is formatted in desired format
        """
        reports = streams.ReportStream("", "", "")

        response = {
            "Header": {
                "Time": "2021-07-22T05:51:37-07:00",
                "ReportName": "ProfitAndLoss",
                "ReportBasis": "Accrual",
                "StartPeriod": "2021-07-20",
                "EndPeriod": "2021-07-21",
                "SummarizeColumnsBy": "Days",
                "Currency": "USD",
                "Option": [{
                    "Name": "AccountingStandard",
                    "Value": "GAAP"
                }, {
                    "Name": "NoReportData",
                    "Value": "true"
                }]
            },
            "Columns": {
                "Column": [{
                    "ColTitle": "",
                    "ColType": "Account",
                    "MetaData": [{
                        "Name": "ColKey",
                        "Value": "account"
                    }]
                }, {
                    "ColTitle": "Jul 20, 2021",
                    "ColType": "Money",
                    "MetaData": [{
                        "Name": "StartDate",
                        "Value": "2021-07-20"
                    }, {
                        "Name": "EndDate",
                        "Value": "2021-07-20"
                    }, {
                        "Name": "ColKey",
                        "Value": "Jul 20, 2021"
                    }]
                }, {
                    "ColTitle": "Jul 21, 2021",
                    "ColType": "Money",
                    "MetaData": [{
                        "Name": "StartDate",
                        "Value": "2021-07-21"
                    }, {
                        "Name": "EndDate",
                        "Value": "2021-07-21"
                    }, {
                        "Name": "ColKey",
                        "Value": "Jul 21, 2021"
                    }]
                }, {
                    "ColTitle": "Total",
                    "ColType": "Money",
                    "MetaData": [{
                        "Name": "ColKey",
                        "Value": "total"
                    }]
                }]
            },
            "Rows": {
                "Row": [{
                    "Header": {
                        "ColData": [{
                            "value": "Income"
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }]
                    },
                    "Summary": {
                        "ColData": [{
                            "value": "Total Income"
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }, {
                            "value": "0.00"
                        }]
                    },
                    "type": "Section",
                    "group": "Income"
                }, {
                    "Summary": {
                        "ColData": [{
                            "value": "Gross Profit"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }]
                    },
                    "type": "Section",
                    "group": "GrossProfit"
                }, {
                    "Header": {
                        "ColData": [{
                            "value": "Expenses"
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }]
                    },
                    "Summary": {
                        "ColData": [{
                            "value": "Total Expenses"
                        }, {
                            "value": ""
                        }, {
                            "value": ""
                        }, {
                            "value": "0.00"
                        }]
                    },
                    "type": "Section",
                    "group": "Expenses"
                }, {
                    "Summary": {
                        "ColData": [{
                            "value": "Net Operating Income"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }]
                    },
                    "type": "Section",
                    "group": "NetOperatingIncome"
                }, {
                    "Summary": {
                        "ColData": [{
                            "value": "Net Income"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }, {
                            "value": "0.00"
                        }]
                    },
                    "type": "Section",
                    "group": "NetIncome"
                }]
            }
        }

        expected_data_after_parse_columns = {
            "dates": ["2021-07-20", "2021-07-21"],
            "data": []
        }

        expected_data_after_parse_rows = {
            "dates": ["2021-07-20", "2021-07-21"],
            "data": [{
                "name": "Total Income",
                "values": ["", "", "0.00"]
            }, {
                "name": "Gross Profit",
                "values": ["0.00", "0.00", "0.00"]
            }, {
                "name": "Total Expenses",
                "values": ["", "", "0.00"]
            }, {
                "name": "Net Operating Income",
                "values": ["0.00", "0.00", "0.00"]
            }, {
                "name": "Net Income",
                "values": ["0.00", "0.00", "0.00"]
            }]
        }

        reports.parse_report_columns(response['Columns'])
        self.assertEqual(reports.parsed_metadata, expected_data_after_parse_columns)

        reports.parse_report_rows(response["Rows"])
        self.assertEqual(reports.parsed_metadata, expected_data_after_parse_rows)
    


class TestGeneralLedgerParser(unittest.TestCase):

    RESPONSE = {
        "Columns": {"Column": [
            {"ColTitle": "Date", "MetaData": [{"Name": "ColKey", "Value": "tx_date"}]},
            {"ColTitle": "Transaction Type", "MetaData": [{"Name": "ColKey", "Value": "txn_type"}]},
            {"ColTitle": "Num", "MetaData": [{"Name": "ColKey", "Value": "doc_num"}]},
            {"ColTitle": "Name", "MetaData": [{"Name": "ColKey", "Value": "name"}]},
            {"ColTitle": "Memo", "MetaData": [{"Name": "ColKey", "Value": "memo"}]},
            {"ColTitle": "Split", "MetaData": [{"Name": "ColKey", "Value": "split_acc"}]},
            {"ColTitle": "Debit", "MetaData": [{"Name": "ColKey", "Value": "debt_amt"}]},
            {"ColTitle": "Credit", "MetaData": [{"Name": "ColKey", "Value": "credit_amt"}]},
            {"ColTitle": "Balance", "MetaData": [{"Name": "ColKey", "Value": "rbal_nat_amount"}]},
        ]},
        "Rows": {"Row": [
            {"type": "Section",
             "Header": {"ColData": [{"value": "Payroll Expenses", "id": "10"}]},
             "Rows": {"Row": [
                 {"type": "Data", "ColData": [
                     {"value": "Beginning Balance"}, {"value": ""}, {"value": ""}, {"value": ""},
                     {"value": ""}, {"value": ""}, {"value": ""}, {"value": ""}, {"value": "0.00"}]},
                 {"type": "Data", "ColData": [
                     {"value": "2024-01-31"}, {"value": "Payroll Check", "id": "55"}, {"value": "7"},
                     {"value": "Jane"}, {"value": "Wages"}, {"value": "Bank"}, {"value": "1,250.50"},
                     {"value": ""}, {"value": "1250.50"}]},
             ]},
             "Summary": {"ColData": [{"value": "Total for Payroll Expenses"}]}},
            {"type": "Section",
             "Header": {"ColData": [{"value": "Payroll Liabilities", "id": "20"}]},
             "Rows": {"Row": [
                 {"type": "Section",
                  "Header": {"ColData": [{"value": "Federal Taxes", "id": "21"}]},
                  "Rows": {"Row": [
                      {"type": "Data", "ColData": [
                          {"value": "2024-01-31"}, {"value": "Payroll Check", "id": "55"}, {"value": "7"},
                          {"value": ""}, {"value": "Tax"}, {"value": "Bank"}, {"value": ""},
                          {"value": "100.00"}, {"value": "100.00"}]},
                  ]}},
             ]}},
        ]},
    }

    def test_parse_report(self):
        stream = streams.GeneralLedgerReport("", "", "")
        records = list(stream.parse_report(self.RESPONSE))

        self.assertEqual(2, len(records))
        wages, tax = records
        self.assertEqual("10", wages["AccountId"])
        self.assertEqual("Payroll Expenses", wages["AccountName"])
        self.assertEqual("55", wages["TxnId"])
        self.assertEqual("Payroll Check", wages["TxnType"])
        self.assertEqual("7", wages["DocNumber"])
        self.assertEqual((1250.5, 0.0), (wages["Debit"], wages["Credit"]))
        # nested section: innermost account wins
        self.assertEqual("21", tax["AccountId"])
        self.assertEqual((0.0, 100.0), (tax["Debit"], tax["Credit"]))
        self.assertNotEqual(wages["RowKey"], tax["RowKey"])

    def test_identical_lines_get_unique_keys(self):
        response = {"Columns": self.RESPONSE["Columns"], "Rows": {"Row": [
            {"type": "Section", "Header": {"ColData": [{"value": "A", "id": "1"}]},
             "Rows": {"Row": [self.RESPONSE["Rows"]["Row"][0]["Rows"]["Row"][1]] * 2}}]}}
        records = list(streams.GeneralLedgerReport("", "", "").parse_report(response))
        self.assertEqual(2, len(records))
        self.assertNotEqual(records[0]["RowKey"], records[1]["RowKey"])

    def test_window_split_on_bad_request(self):
        from unittest import mock
        from tap_quickbooks.client import QuickbooksBadRequestError

        client = mock.Mock()
        client.minor_version = 65
        calls = []

        def get(endpoint, params=None):
            calls.append((params["start_date"], params["end_date"]))
            if params["start_date"] == "2024-01-01" and params["end_date"] == "2024-01-04":
                raise QuickbooksBadRequestError("too large")
            return {"Columns": {"Column": []}, "Rows": {}}

        client.get.side_effect = get
        stream = streams.GeneralLedgerReport(client, {}, {})
        list(stream.sync_window(datetime.date(2024, 1, 1), datetime.date(2024, 1, 4)))
        self.assertEqual([("2024-01-01", "2024-01-04"), ("2024-01-01", "2024-01-02"),
                          ("2024-01-03", "2024-01-04")], calls)

    def test_edited_line_keeps_its_key(self):
        """An amount/memo edit must overwrite the old row, not create a second one"""
        import copy
        original = list(streams.GeneralLedgerReport("", "", "").parse_report(self.RESPONSE))
        edited = copy.deepcopy(self.RESPONSE)
        line = edited["Rows"]["Row"][0]["Rows"]["Row"][1]["ColData"]
        line[4]["value"] = "Wages (corrected)"
        line[6]["value"] = "1,300.00"
        records = list(streams.GeneralLedgerReport("", "", "").parse_report(edited))
        self.assertEqual(original[0]["RowKey"], records[0]["RowKey"])
        self.assertEqual(1300.0, records[0]["Debit"])

    def test_missing_required_columns_raises(self):
        response = {"Columns": {"Column": [
            {"MetaData": [{"Name": "ColKey", "Value": "tx_date"}]},
            {"MetaData": [{"Name": "ColKey", "Value": "not_a_column"}]},
        ]}, "Rows": {}}
        with self.assertRaises(Exception) as ctx:
            list(streams.GeneralLedgerReport("", "", "").parse_report(response))
        self.assertIn("txn_type", str(ctx.exception))
        self.assertIn("debt_amt", str(ctx.exception))

    def test_empty_report_yields_nothing(self):
        self.assertEqual([], list(streams.GeneralLedgerReport("", "", "").parse_report({})))

    def test_backdated_line_keeps_its_key(self):
        import copy
        original = list(streams.GeneralLedgerReport("", "", "").parse_report(self.RESPONSE))
        moved = copy.deepcopy(self.RESPONSE)
        moved["Rows"]["Row"][0]["Rows"]["Row"][1]["ColData"][0]["value"] = "2024-01-15"
        records = list(streams.GeneralLedgerReport("", "", "").parse_report(moved))
        self.assertEqual(original[0]["RowKey"], records[0]["RowKey"])


class TestGeneralLedgerSync(unittest.TestCase):
    NOW = datetime.datetime(2024, 3, 15, 10, 0, tzinfo=datetime.timezone.utc)

    def run_sync(self, config, state):
        from unittest import mock
        client = mock.Mock()
        client.minor_version = 65
        client.get.return_value = {"Columns": {"Column": []}, "Rows": {}}
        base = {"start_date": "2024-01-01T00:00:00Z"}
        base.update(config)
        stream = streams.GeneralLedgerReport(client, base, state)
        with mock.patch.object(streams.utils, "now", return_value=self.NOW), \
                mock.patch.object(streams.singer, "write_state"):
            list(stream.sync())
        windows = [(c.kwargs["params"]["start_date"], c.kwargs["params"]["end_date"])
                   for c in client.get.call_args_list]
        return windows, stream.state

    def test_first_sync_walks_windows_from_start_date_to_today(self):
        windows, state = self.run_sync({}, {})
        self.assertEqual([("2024-01-01", "2024-01-31"), ("2024-02-01", "2024-03-02"),
                          ("2024-03-03", "2024-03-15")], windows)
        self.assertEqual("2024-03-15T00:00:00+00:00",
                         state["bookmarks"]["general_ledger_report"]["LastUpdatedTime"])

    def test_bookmark_sync_rereads_lookback_window(self):
        state = {"bookmarks": {"general_ledger_report": {"LastUpdatedTime": "2024-03-10T00:00:00+00:00"}}}
        windows, _ = self.run_sync({"general_ledger_lookback_days": "10"}, state)
        self.assertEqual([("2024-02-29", "2024-03-15")], windows)

    def test_lookback_never_goes_before_start_date(self):
        state = {"bookmarks": {"general_ledger_report": {"LastUpdatedTime": "2024-01-05T00:00:00+00:00"}}}
        windows, _ = self.run_sync({}, state)
        self.assertEqual("2024-01-01", windows[0][0])

    def test_request_params(self):
        from unittest import mock
        client = mock.Mock()
        client.minor_version = 65
        client.get.return_value = {"Columns": {"Column": []}, "Rows": {}}
        stream = streams.GeneralLedgerReport(client, {"general_ledger_accounting_method": "Cash"}, {})
        list(stream.sync_window(datetime.date(2024, 1, 1), datetime.date(2024, 1, 31)))
        params = client.get.call_args.kwargs["params"]
        self.assertEqual("Cash", params["accounting_method"])
        self.assertEqual(streams.GeneralLedgerReport.DEFAULT_COLUMNS, params["columns"])
        self.assertEqual("/v3/company/{realm_id}/reports/GeneralLedger", client.get.call_args.args[0])
