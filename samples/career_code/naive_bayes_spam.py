from fractions import Fraction as F

# 8 training emails: (is_spam, words in the email)
emails = [
    (True, {"free", "win"}), (True, {"free", "win"}), (True, {"free"}), (True, {"meeting"}),
    (False, {"free"}), (False, {"win", "meeting"}), (False, {"meeting"}), (False, {"homework"}),
]
new_email = ["free", "win"]

spam = [words for is_spam, words in emails if is_spam]
ham = [words for is_spam, words in emails if not is_spam]


def p_word(word, group):  # fraction of emails in the group that contain the word
    return F(sum(word in words for words in group), len(group))


score_spam = F(len(spam), len(emails))  # P(spam)
score_ham = F(len(ham), len(emails))    # P(ham)
for word in new_email:                  # "naive": multiply one fraction per word
    score_spam *= p_word(word, spam)
    score_ham *= p_word(word, ham)

p_spam = score_spam / (score_spam + score_ham)
print("score_spam =", score_spam, " score_ham =", score_ham, " P(spam) =", p_spam)
