from flask import Flask, render_template, request, flash, send_file, session, redirect, url_for
import re
import io

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Function to validate input
def validate_input(value):
    return re.match(r'^[A-Z0-9_][A-Z0-9._-]*[A-Z0-9_]$', value) is not None

# Function to generate MQSC script
def generate_mqsc(names, selected_object, qmgr_name):
    errors = []
    max_length = 48 if "Queue" in selected_object else 20
    valid_names = []

    for name in names:
        name = name.strip()
        if name:
            if len(name) > max_length:
                errors.append(f"{selected_object} '{name}' exceeds {max_length} characters limit.")
            elif not validate_input(name):
                errors.append(f"{selected_object} '{name}' contains invalid characters.")
            else:
                valid_names.append(name)

    valid_names = list(set(valid_names))  # Remove duplicates

    if errors:
        return None, errors

    script = f"\n* ********** {selected_object} **********\n"
    command_template = {
        "Local Queue": "DEFINE QLOCAL({}) DESCR('User-defined local queue') MAXDEPTH(5000) DEFTYPE(PREDEFINED) REPLACE",
        "Remote Queue": "DEFINE QREMOTE({}) RNAME('TARGET.QUEUE') RQMNAME('TARGETQM') XMITQ('TRANSMIT.QUEUE') DESCR('Remote queue mapping') REPLACE",
        "Alias Queue": "DEFINE QALIAS({}) TARGET('BASE.QUEUE') TARGTYPE(QUEUE) DESCR('Alias queue reference') REPLACE",
        "Sender Channel": "DEFINE CHANNEL({}) CHLTYPE(SDR) TRPTYPE(TCP) CONNAME('TARGET.HOST(1414)') XMITQ('XMITQ') SSLCIPH('TLS_RSA_WITH_AES_128_CBC_SHA256') DESCR('Sender channel') REPLACE",
        "Receiver Channel": "DEFINE CHANNEL({}) CHLTYPE(RCVR) TRPTYPE(TCP) SSLCIPH('TLS_RSA_WITH_AES_128_CBC_SHA256') DESCR('Receiver channel') REPLACE",
        "Server-Connection Channel": "DEFINE CHANNEL({}) CHLTYPE(SVRCONN) MCAUSER('mqm') DESCR('Server-connection channel') REPLACE",
    }

    for name in valid_names:
        script += command_template[selected_object].format(f"{qmgr_name}.{name}") + "\n"

    return script, None

@app.route('/', methods=['GET', 'POST'])
def index():
    mq_object_types = ["Local Queue", "Remote Queue", "Alias Queue", "Sender Channel", "Receiver Channel", "Server-Connection Channel"]
    if 'scripts' not in session:
        session['scripts'] = []

    if request.method == 'POST':
        selected_object = request.form['mq_object_type']
        names = request.form['names'].strip().split('\n')
        qmgr_name = request.form['qmgr_name'].strip()

        if not any(names):
            flash('Input field cannot be blank!', 'error')
        elif not qmgr_name:
            flash('QMGR Name cannot be blank!', 'error')
        else:
            script, errors = generate_mqsc(names, selected_object, qmgr_name)

            if errors:
                for error in errors:
                    flash(error, 'error')
            else:
                session['scripts'].append(script)
                flash('Script generated successfully!', 'success')

    return render_template('index.html', mq_object_types=mq_object_types, scripts=session['scripts'])

@app.route('/download', methods=['POST'])
def download():
    scripts = "\n".join(session['scripts'])
    return send_file(
        io.BytesIO(scripts.encode()),
        as_attachment=True,
        download_name='output.mqsc',
        mimetype='text/plain'
    )

@app.route('/clear', methods=['POST'])
def clear():
    session['scripts'] = []
    flash('Output cleared successfully!', 'success')
    return redirect(url_for('index'))

if __name__ == '__main__':
    app.run(debug=True)
