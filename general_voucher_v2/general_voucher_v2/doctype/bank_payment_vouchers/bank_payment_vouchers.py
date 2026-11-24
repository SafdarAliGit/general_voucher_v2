# Copyright (c) 2023, Tech Ventures and contributors
# For license information, please see license.txt
import frappe
# import frappe
from frappe.model.document import Document
from frappe.model.naming import make_autoname
from general_voucher_v2.general_voucher_v2.doctype.utils_functions import get_doctype_by_field


class BankPaymentVouchers(Document):
    def before_submit(self):
        je_present = get_doctype_by_field('Journal Entry', 'bill_no', self.name)
        company = self.company
        cost_center = frappe.get_cached_value("Company", company, "cost_center")
        bank_account = self.account
        posting_date = self.posting_date
        voucher_type = "Bank Entry"
        crv_no = self.name
        cheque_no = crv_no
        cheque_date = posting_date
        total = self.total
        if len(self.items) > 0 and int(self.bpv_status) < 1 and not je_present:
            je = frappe.new_doc("Journal Entry")
            je.posting_date = posting_date
            je.voucher_type = voucher_type
            je.company = company
            je.bill_no = crv_no
            je.cheque_no = cheque_no,
            je.cheque_date = cheque_date,
            for item in self.items:
                operating_unit = getattr(item, 'operating_unit', None)
                first_row = {
                    'account': item.account,
                    'party_type': item.party_type,
                    'party': item.party,
                    'user_remark': f"{item.description}, Ref:{item.ref_no}",
                    'reference_due_date': item.ref_date if item.ref_date else None,
                    'debit_in_account_currency': item.amount,
                    'credit_in_account_currency': 0,
                    'cost_center': cost_center
                }
                second_row = {
                    'account': bank_account,
                    'debit_in_account_currency': 0,
                    'user_remark': f"{item.description}, Ref:{item.ref_no}",
                    'reference_due_date': item.ref_date if item.ref_date else None,
                    'credit_in_account_currency': item.amount,
                    'cost_center': cost_center
                }
                if operating_unit:
                    first_row['custom_operating_unit'] = operating_unit
                    second_row['custom_operating_unit'] = operating_unit
                je.append("accounts", first_row)
                je.append("accounts", second_row)
            je.submit()
            frappe.db.set_value('Bank Payment Vouchers', self.name, 'bpv_status', 1)
        else:
            if len(self.items) < 1:
                frappe.throw("No detailed rows found")
            if self.bpv_status > 0:
                frappe.throw("Journal entry already created")

    def on_cancel(self):
        current_je = get_doctype_by_field('Journal Entry', 'bill_no', self.name)
        if current_je:
            if current_je.docstatus != 2:  # Ensure the document is in the "Submitted" state
                current_je.cancel()
                frappe.db.commit()
            else:
                frappe.throw("Document is not in the 'Submitted' state.")
            if current_je.amended_from:
                new_name = int(current_je.name.split("-")[-1]) + 1
            else:
                new_name = f"{current_je.name}-{1}"
            make_autoname(new_name, 'Journal Entry')
