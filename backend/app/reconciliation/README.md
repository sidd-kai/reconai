# Reconciliation engine

Initial baseline rules:
1. Exact reference match + exact amount.
2. Exact reference match + acceptable timestamp delta.
3. Candidate fuzzy match using identifier, amount, timestamp, and customer reference features.
4. Settlement validation: gross - fee - tax = net.
5. Ambiguous or unsafe cases become exceptions, never forced matches.
