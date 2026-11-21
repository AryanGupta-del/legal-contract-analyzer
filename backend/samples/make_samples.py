"""Generates two fictional SaaS agreements for the in-app demo and for tests.

Run:  python samples/make_samples.py
"""
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer

OUT = Path(__file__).parent

CONTRACTS = {
    "sample_saas_agreement_A.pdf": {
        "title": "SOFTWARE-AS-A-SERVICE AGREEMENT",
        "intro": "This Agreement is made on 1 March 2026 between Nimbus Analytics Pvt Ltd "
                 "(\"Provider\") and Acme Retail Ltd (\"Customer\").",
        "clauses": [
            ("1. Term", "This Agreement begins on the Effective Date and continues for twelve (12) "
             "months. It automatically renews for successive twelve-month renewal terms unless "
             "either party gives written notice of non-renewal at least ninety (90) days before "
             "the end of the then-current term."),
            ("2. Fees and Payment", "Customer shall pay the annual fee of USD 48,000 in advance. "
             "All fees are non-refundable. Late payments accrue interest at 2% per month, and "
             "Provider may suspend the service after seven (7) days of non-payment."),
            ("3. Termination", "Customer may terminate for convenience only during the first "
             "thirty (30) days and must pay a termination penalty equal to fifty percent (50%) of "
             "the remaining annual fees. Provider may terminate for convenience at any time on "
             "fourteen (14) days' notice without refund."),
            ("4. Limitation of Liability", "Provider's total liability shall not exceed the fees "
             "paid in the preceding one (1) month. Provider is not liable for any indirect or "
             "consequential damages. Customer's liability for breach is unlimited."),
            ("5. Indemnification", "Customer shall indemnify and hold harmless Provider against "
             "all claims, losses and expenses arising from Customer's use of the service. "
             "Provider gives no indemnity of any kind."),
            ("6. Confidentiality", "Each party shall keep the other's confidential information "
             "secret for five (5) years after termination."),
            ("7. Intellectual Property", "Customer assigns to Provider all rights in any feedback, "
             "data models and work product created using the service."),
            ("8. Governing Law and Disputes", "This Agreement is governed by the laws of "
             "Singapore. All disputes shall be finally resolved by binding arbitration in "
             "Singapore, and Customer waives any right to participate in a class action."),
        ],
    },
    "sample_saas_agreement_B.pdf": {
        "title": "SERVICES AGREEMENT",
        "intro": "This Agreement is made on 15 April 2026 between BrightDesk Software Inc "
                 "(\"Vendor\") and Acme Retail Ltd (\"Client\").",
        "clauses": [
            ("1. Term", "This Agreement runs for twelve (12) months. It does not renew "
             "automatically; renewal requires a written order signed by both parties."),
            ("2. Fees and Payment", "Client shall pay USD 42,000 per year in quarterly "
             "instalments, due thirty (30) days after invoice. Fees for unused periods are "
             "refunded pro rata if Client terminates for Vendor's uncured breach."),
            ("3. Termination", "Either party may terminate for convenience on sixty (60) days' "
             "written notice. Client then pays only for services delivered up to the termination "
             "date. No termination penalty applies."),
            ("4. Limitation of Liability", "Each party's total liability is capped at the fees "
             "paid or payable in the twelve (12) months preceding the claim, except for "
             "confidentiality breaches and wilful misconduct."),
            ("5. Indemnification", "Each party shall indemnify the other against third-party "
             "claims arising from its own negligence. Vendor indemnifies Client against "
             "third-party intellectual property infringement claims."),
            ("6. Confidentiality", "Each party shall protect the other's confidential "
             "information for three (3) years after termination."),
            ("7. Intellectual Property", "Client retains all rights in its data and outputs. "
             "Vendor retains rights in the underlying software."),
            ("8. Governing Law and Disputes", "This Agreement is governed by the laws of India. "
             "The courts of Bengaluru have non-exclusive jurisdiction."),
        ],
    },
}


def build(path: Path, spec: dict) -> None:
    ss = getSampleStyleSheet()
    title = ParagraphStyle("t", parent=ss["Title"], fontSize=16, spaceAfter=14)
    head = ParagraphStyle("h", parent=ss["Heading4"], spaceBefore=10, spaceAfter=2)
    body = ParagraphStyle("b", parent=ss["BodyText"], leading=14)
    story = [Paragraph(spec["title"], title), Paragraph(spec["intro"], body), Spacer(1, 8)]
    for heading, text in spec["clauses"]:
        story += [Paragraph(heading + ".", head), Paragraph(text, body)]
    SimpleDocTemplate(str(path), pagesize=A4, title=spec["title"]).build(story)


if __name__ == "__main__":
    for name, spec in CONTRACTS.items():
        build(OUT / name, spec)
        print("wrote", OUT / name)
