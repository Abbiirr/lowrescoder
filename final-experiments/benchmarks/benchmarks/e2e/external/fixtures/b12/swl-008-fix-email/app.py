"""Flask API for email template rendering — variable name mismatch bug."""
from flask import Flask, jsonify, request

app = Flask(__name__)

# Email templates use {name} placeholder
TEMPLATES = {
    "welcome": {
        "subject": "Welcome, {name}!",
        "body": "Hello {name},\n\nWelcome to our platform! We're glad to have you.",
    },
    "reset": {
        "subject": "Password Reset for {name}",
        "body": "Hi {name},\n\nClick the link below to reset your password.",
    },
    "invoice": {
        "subject": "Invoice for {name}",
        "body": "Dear {name},\n\nPlease find your invoice attached.\nAmount: {amount}",
    },
}


@app.route("/api/templates")
def list_templates():
    return jsonify({"templates": list(TEMPLATES.keys())})


@app.route("/api/render", methods=["POST"])
def render_template():
    data = request.get_json()
    template_id = data.get("template")
    variables = data.get("variables", {})

    if template_id not in TEMPLATES:
        return jsonify({"error": "template not found"}), 404

    tpl = TEMPLATES[template_id]
    # BUG: the frontend sends "username" but templates expect "name"
    # This renders the template with un-substituted {name} placeholders
    try:
        rendered_subject = tpl["subject"].format(**variables)
        rendered_body = tpl["body"].format(**variables)
    except KeyError as e:
        return jsonify({"error": f"missing variable: {e}"}), 400

    return jsonify({
        "subject": rendered_subject,
        "body": rendered_body,
    })


if __name__ == "__main__":
    app.run(debug=True)
