"""
Baseline model: Gaussian Naive Bayes.
"""

from sklearn.naive_bayes import GaussianNB


def get_naive_bayes():
    """
    Return a configured Gaussian Naive Bayes classifier.

    Complexity: θ(N·d)  where N = training size, d = number of features.
    """
    return GaussianNB()
