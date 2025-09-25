from flask import Flask, request, render_template_string, jsonify
import csv
import io
import os
from werkzeug.utils import secure_filename
import re
from collections import OrderedDict

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Create uploads directory if it doesn't exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Regex Pattern Generator for Colab</title>
    <style>
        body { 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            max-width: 1200px; 
            margin: 0 auto; 
            padding: 20px; 
            background-color: #f5f5f5; 
        }
        .container { 
            background: white; 
            padding: 30px; 
            border-radius: 10px; 
            box-shadow: 0 2px 10px rgba(0,0,0,0.1); 
        }
        h1 { 
            color: #333; 
            border-bottom: 3px solid #007bff; 
            padding-bottom: 10px; 
        }
        .upload-section { 
            background: #f8f9fa; 
            padding: 20px; 
            border-radius: 8px; 
            margin: 20px 0; 
            border: 2px dashed #007bff; 
        }
        .file-input { 
            padding: 10px; 
            border: 1px solid #ddd; 
            border-radius: 5px; 
            margin-right: 10px; 
        }
        .btn { 
            background: #007bff; 
            color: white; 
            padding: 12px 24px; 
            border: none; 
            border-radius: 5px; 
            cursor: pointer; 
            font-size: 16px; 
        }
        .btn:hover { background: #0056b3; }
        .format-info { 
            background: #e9ecef; 
            padding: 15px; 
            border-radius: 5px; 
            margin: 15px 0; 
        }
        .code-output { 
            background: #f8f9fa; 
            border: 1px solid #e9ecef; 
            border-radius: 5px; 
            padding: 15px; 
            margin: 20px 0; 
            max-height: 600px; 
            overflow-y: auto; 
        }
        .copy-btn { 
            background: #28a745; 
            margin-top: 10px; 
        }
        .copy-btn:hover { background: #1e7e34; }
        pre { 
            margin: 0; 
            white-space: pre-wrap; 
            font-family: 'Courier New', monospace; 
            font-size: 12px; 
            line-height: 1.4; 
        }
        .error { 
            color: #dc3545; 
            background: #f8d7da; 
            padding: 10px; 
            border-radius: 5px; 
            border: 1px solid #f5c6cb; 
        }
        .success { 
            color: #155724; 
            background: #d4edda; 
            padding: 10px; 
            border-radius: 5px; 
            border: 1px solid #c3e6cb; 
        }
        .stats { 
            display: flex; 
            gap: 20px; 
            margin: 15px 0; 
        }
        .stat-box { 
            background: #007bff; 
            color: white; 
            padding: 15px; 
            border-radius: 5px; 
            text-align: center; 
            flex: 1; 
        }
        table { 
            width: 100%; 
            border-collapse: collapse; 
            margin: 15px 0; 
        }
        th, td { 
            border: 1px solid #ddd; 
            padding: 8px; 
            text-align: left; 
        }
        th { background: #f2f2f2; }
    </style>
</head>
<body>
    <div class="container">
        <h1>🎯 Regex Pattern Generator for Google Colab</h1>
        <p>Upload a CSV file to generate the REGEX_PATTERNS OrderedDict for Cell 2 of your Colab notebook.</p>
        
        <div class="format-info">
            <h3>📋 Expected CSV Format:</h3>
            <p>Your CSV should contain the following columns (column names are case-insensitive):</p>
            <table>
                <tr><th>Column Name</th><th>Description</th><th>Example</th></tr>
                <tr><td>pattern_name</td><td>Name/key for the pattern</td><td>Home</td></tr>
                <tr><td>pattern</td><td>Regex pattern</td><td>^https://www\.payscale\.com/$</td></tr>
                <tr><td>description</td><td>Human-readable description</td><td>Home Page</td></tr>
                <tr><td>color</td><td>Hex color code (optional)</td><td>#87CEEB</td></tr>
                <tr><td>priority</td><td>Priority number (optional, defaults to 1)</td><td>1</td></tr>
            </table>
            <p><strong>Note:</strong> Patterns will be processed in the order they appear in your CSV file.</p>
        </div>

        <div class="upload-section">
            <form id="uploadForm" enctype="multipart/form-data">
                <input type="file" name="file" accept=".csv" class="file-input" id="fileInput" required>
                <button type="submit" class="btn">🚀 Generate Patterns</button>
            </form>
        </div>

        <div id="result"></div>
    </div>

    <script>
        document.getElementById('uploadForm').addEventListener('submit', async function(e) {
            e.preventDefault();
            
            const fileInput = document.getElementById('fileInput');
            const file = fileInput.files[0];
            
            if (!file) {
                alert('Please select a CSV file');
                return;
            }

            const formData = new FormData();
            formData.append('file', file);

            try {
                const response = await fetch('/generate', {
                    method: 'POST',
                    body: formData
                });

                const result = await response.json();
                
                if (result.success) {
                    displayResult(result);
                } else {
                    displayError(result.error);
                }
            } catch (error) {
                displayError('Upload failed: ' + error.message);
            }
        });

        function displayResult(result) {
            const html = `
                <div class="success">✅ Successfully generated ${result.pattern_count} patterns!</div>
                
                <div class="stats">
                    <div class="stat-box">
                        <h4>${result.pattern_count}</h4>
                        <p>Total Patterns</p>
                    </div>
                    <div class="stat-box">
                        <h4>${result.priorities}</h4>
                        <p>Priority Levels</p>
                    </div>
                    <div class="stat-box">
                        <h4>${result.csv_rows}</h4>
                        <p>CSV Rows</p>
                    </div>
                </div>

                <h3>📄 Generated Code for Cell 2:</h3>
                <p>Copy the code below and paste it into Cell 2 of your Colab notebook to replace the REGEX_PATTERNS dictionary:</p>
                
                <div class="code-output">
                    <pre id="generatedCode">${result.code}</pre>
                </div>
                
                <button class="btn copy-btn" onclick="copyToClipboard()">📋 Copy to Clipboard</button>
            `;
            
            document.getElementById('result').innerHTML = html;
        }

        function displayError(error) {
            document.getElementById('result').innerHTML = `
                <div class="error">❌ Error: ${error}</div>
            `;
        }

        function copyToClipboard() {
            const code = document.getElementById('generatedCode').textContent;
            navigator.clipboard.writeText(code).then(function() {
                alert('Code copied to clipboard!');
            }, function(err) {
                alert('Failed to copy code. Please select and copy manually.');
            });
        }
    </script>
</body>
</html>
'''

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() == 'csv'

def clean_pattern_name(name):
    """Clean and format pattern name for use as dictionary key"""
    # Remove special characters and normalize spacing
    cleaned = re.sub(r'[^\w\s-]', '', str(name))
    cleaned = re.sub(r'\s+', ' ', cleaned).strip()
    return cleaned

def escape_regex_for_string(pattern):
    """Escape only single quotes in regex patterns for raw Python string literals"""
    # For raw strings (r'...'), only escape single quotes, not backslashes
    escaped = pattern.replace("'", "\\'")
    return escaped

def generate_default_color(index):
    """Generate default colors cycling through a predefined palette"""
    colors = [
        '#87CEEB', '#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', 
        '#FFEAA7', '#DDA0DD', '#B19CD9', '#FF9F43', '#F0A3A3'
    ]
    return colors[index % len(colors)]

def process_csv_to_patterns(csv_file):
    """Convert CSV file to REGEX_PATTERNS OrderedDict format using built-in csv module"""
    try:
        # Read the CSV file content as text
        content = csv_file.read().decode('utf-8')
        
        # Parse CSV using built-in csv module
        csv_reader = csv.DictReader(io.StringIO(content))
        rows = list(csv_reader)
        
        if not rows:
            raise ValueError("No data rows found in CSV file")
        
        # Normalize column names (lowercase, strip spaces)
        normalized_rows = []
        for row in rows:
            normalized_row = {}
            for key, value in row.items():
                if key:  # Skip None keys
                    normalized_key = key.lower().strip()
                    normalized_row[normalized_key] = value
            normalized_rows.append(normalized_row)
        
        # Map common column name variations
        column_mapping = {
            'name': 'pattern_name',
            'regex': 'pattern',
            'regex_pattern': 'pattern',
            'pattern_regex': 'pattern',
            'desc': 'description',
            'colour': 'color',
            'hex_color': 'color',
            'priority_level': 'priority',
            'processing_order': 'priority',
            'order': 'priority'
        }
        
        # Apply column mapping and fill defaults
        processed_rows = []
        for i, row in enumerate(normalized_rows):
            # Apply column mapping
            mapped_row = {}
            for original_key, mapped_key in column_mapping.items():
                if original_key in row and mapped_key not in row:
                    mapped_row[mapped_key] = row[original_key]
            
            # Merge mapped columns back
            for key, value in row.items():
                mapped_row[key] = value
            
            # Check required columns
            if 'pattern_name' not in mapped_row or 'pattern' not in mapped_row:
                continue  # Skip rows missing required fields
            
            if not mapped_row.get('pattern_name') or not mapped_row.get('pattern'):
                continue  # Skip empty required fields
            
            # Fill missing values
            if 'description' not in mapped_row or not mapped_row.get('description'):
                mapped_row['description'] = mapped_row['pattern_name']
            
            if 'priority' not in mapped_row or not mapped_row.get('priority'):
                mapped_row['priority'] = '1'
            else:
                try:
                    mapped_row['priority'] = str(int(float(mapped_row['priority'])))
                except (ValueError, TypeError):
                    mapped_row['priority'] = '1'
            
            if 'color' not in mapped_row or not mapped_row.get('color'):
                mapped_row['color'] = generate_default_color(i)
            else:
                color = mapped_row['color']
                if not str(color).startswith('#'):
                    mapped_row['color'] = f'#{color}'
            
            processed_rows.append(mapped_row)
        
        if not processed_rows:
            raise ValueError("No valid rows found in CSV file. Check that pattern_name and pattern columns exist and are not empty.")
        
        # Sort by priority if specified
        processed_rows.sort(key=lambda x: (int(x.get('priority', 1)), x.get('pattern_name', '')))
        
        # Generate the Python code
        code_lines = [
            "# Global pattern library - edit and expand as needed",
            "# IMPORTANT: Patterns are processed in ORDER - put more specific patterns FIRST!",
            "",
            "REGEX_PATTERNS = OrderedDict(["
        ]
        
        for row in processed_rows:
            pattern_name = clean_pattern_name(row['pattern_name'])
            pattern = escape_regex_for_string(str(row['pattern']))
            description = str(row['description']).replace("'", "\\'")
            color = row['color']
            priority = int(row['priority'])
            
            # Add pattern entry
            code_lines.extend([
                f"    ('{pattern_name}', {{",
                f"        'pattern': r'{pattern}',",
                f"        'description': '{description}',",
                f"        'color': '{color}',",
                f"        'priority': {priority}",
                f"    }}),",
                ""
            ])
        
        code_lines.append("])")
        
        generated_code = "\n".join(code_lines)
        
        # Calculate statistics
        priorities = len(set(row['priority'] for row in processed_rows))
        
        return {
            'success': True,
            'code': generated_code,
            'pattern_count': len(processed_rows),
            'csv_rows': len(processed_rows),
            'priorities': priorities
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/generate', methods=['POST'])
def generate_patterns():
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No file uploaded'})
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({'success': False, 'error': 'No file selected'})
    
    if not allowed_file(file.filename):
        return jsonify({'success': False, 'error': 'Please upload a CSV file'})
    
    try:
        # Process the CSV directly from memory
        result = process_csv_to_patterns(file)
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'error': f'Processing error: {str(e)}'})

if __name__ == '__main__':
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
