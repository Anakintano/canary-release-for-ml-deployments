"""Deterministic synthetic support tickets. The data is fake: templates + random slot values + noise.

`python -m ml.data` prints a few samples.
"""
import random
import re

TEMPLATES = {
    "billing": [
        "I was charged {amount} twice for my {plan} plan",
        "Please refund {amount}, the payment went through but the order failed",
        "My invoice for {month} shows the wrong amount",
        "Why was my card debited {amount} after I cancelled the subscription",
        "Need a GST invoice for order {order}",
        "UPI payment of {amount} failed but the money was deducted from my bank",
        "How do I change the card used for my {plan} subscription",
        "Coupon was not applied at checkout and I paid {amount} extra",
        "Cancel auto renewal on my {plan} plan and refund this month",
        "EMI option is not showing on the payment page",
    ],
    "technical": [
        "The app crashes when I open {feature} on my {device}",
        "Getting error {code} while uploading a file",
        "Page keeps loading forever after the latest update",
        "{feature} is not working on {device} since yesterday",
        "Notifications stopped coming on my {device}",
        "The website shows a blank white screen in {browser}",
        "Sync between my {device} and laptop is broken",
        "Export to PDF fails with error {code}",
        "App is very slow and freezes on the {feature} screen",
        "Buttons do nothing in {browser}, looks like a javascript error",
    ],
    "account": [
        "I forgot my password and the reset email never arrives",
        "Please change the email on my account to {email}",
        "My account got locked after too many login attempts",
        "How do I delete my account permanently",
        "OTP is not coming to my phone number ending {digits}",
        "Someone logged into my account from {city}, I did not do this",
        "I want to update the mobile number on my profile",
        "Two factor authentication is not letting me sign in",
        "Please merge my two accounts into one",
        "Change the name on my profile to {name}",
    ],
    "shipping": [
        "My order {order} has not arrived yet, it was due on {date}",
        "Tracking for {order} has not updated in {days} days",
        "The package was delivered to the wrong address in {city}",
        "{carrier} says delivered but I did not receive anything",
        "Can I change the delivery address for order {order}",
        "Item arrived damaged, the box was torn open",
        "How long does delivery to {city} usually take",
        "Order {order} shows shipped but there is no tracking number",
        "Delivery partner called and cancelled my order {order}",
        "I received the wrong item in order {order}",
    ],
}

SLOTS = {
    "amount": lambda r: r.choice(["?", "Rs ", "INR "]) + str(r.randint(99, 4999)),
    "plan": lambda r: r.choice(["Basic", "Pro", "Premium", "annual", "monthly", "family"]),
    "month": lambda r: r.choice(["January", "March", "June", "August", "October", "December"]),
    "order": lambda r: f"#{r.randint(100000, 999999)}",
    "feature": lambda r: r.choice(["the dashboard", "search", "chat", "reports", "the camera", "settings"]),
    "device": lambda r: r.choice(["iPhone", "Android phone", "Samsung tablet", "Windows laptop", "Mac"]),
    "code": lambda r: f"E{r.randint(100, 999)}",
    "browser": lambda r: r.choice(["Chrome", "Firefox", "Safari", "Edge"]),
    "email": lambda r: r.choice(["priya.s", "rahul88", "anita.k", "dev.m"]) + "@example.com",
    "digits": lambda r: str(r.randint(1000, 9999)),
    "city": lambda r: r.choice(["Pune", "Bengaluru", "Delhi", "Chennai", "Kolkata", "Jaipur", "Mumbai"]),
    "name": lambda r: r.choice(["Priya Sharma", "Rahul Verma", "Jos� Fernandes", "Anita Rao"]),
    "date": lambda r: f"{r.randint(1, 28)} {r.choice(['May', 'July', 'Sept', 'Nov'])}",
    "days": lambda r: str(r.randint(3, 12)),
    "carrier": lambda r: r.choice(["Delhivery", "Blue Dart", "Ekart", "India Post"]),
}

OPENERS = ["", "", "", "Hi,", "Hello team,", "Hey", "URGENT:", "Good morning,", "Dear support,"]
# Two closers are non-ASCII on purpose: real Indian support traffic has them, and demo 2 trips on them.
CLOSERS = ["", "", "", "Thanks", "Please help", "pls help asap", "Thank you ??", "Kindly resolve", "???????", "Waiting for reply"]


def fill(r, template):
    return re.sub(r"\{(\w+)\}", lambda m: SLOTS[m.group(1)](r), template)


def typo(r, text):
    """Swap two adjacent letters in one random word."""
    words = text.split()
    i = r.randrange(len(words))
    w = words[i]
    if len(w) > 3:
        j = r.randrange(len(w) - 1)
        words[i] = w[:j] + w[j + 1] + w[j] + w[j + 2:]
    return " ".join(words)


def make_tickets(n, seed):
    """Return (texts, labels). Same n and seed always give the same tickets."""
    r = random.Random(seed)
    categories = list(TEMPLATES)
    texts, labels = [], []
    for _ in range(n):
        label = r.choice(categories)
        body = fill(r, r.choice(TEMPLATES[label]))
        if r.random() < 0.15:  # customers often mention a second topic, which makes some tickets ambiguous
            body += ". Also " + fill(r, r.choice(TEMPLATES[r.choice(categories)])).lower()
        text = " ".join(p for p in (r.choice(OPENERS), body, r.choice(CLOSERS)) if p)
        for _ in range(r.choice([0, 0, 1, 2])):
            text = typo(r, text)
        if r.random() < 0.1:
            text = text.lower()
        if r.random() < 0.03:  # label noise: human agents mis-tag some tickets
            label = r.choice(categories)
        texts.append(text)
        labels.append(label)
    return texts, labels


if __name__ == "__main__":
    for text, label in zip(*make_tickets(10, seed=0)):
        print(f"{label:<10} {text}")
