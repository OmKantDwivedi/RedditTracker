#!/usr/bin/env python3
"""
Generate a template spreadsheet for users to fill in
"""

import pandas as pd

def create_template():
    """Create template Excel file with example URLs"""
    
    # Sample data with examples
    data = {
        'comment_url': [
            'https://www.reddit.com/r/AskReddit/comments/18q7xe4/what_is_something/keslmx5/',
            'https://www.reddit.com/r/funny/comments/18pz3k1/my_dog_loves_the_snow/ket5r8q/',
            '',  # Empty row (will be skipped)
            '# Add your comment URLs below (delete these examples)',
            '',
            '',
            '',
            '',
        ]
    }
    
    df = pd.DataFrame(data)
    
    # Create Excel file
    output_file = 'reddit_tracker_template.xlsx'
    df.to_excel(output_file, index=False, engine='openpyxl')
    
    print(f"✅ Template created: {output_file}")
    print("\nInstructions:")
    print("1. Open the file in Excel or Google Sheets")
    print("2. Delete the example URLs")
    print("3. Add your Reddit comment URLs (one per row)")
    print("4. Upload to the web interface or use the URL")
    print("\nColumn name: comment_url (do not change!)")

def create_csv_template():
    """Create template CSV file"""
    
    data = {
        'comment_url': [
            'https://www.reddit.com/r/AskReddit/comments/18q7xe4/what_is_something/keslmx5/',
            'https://www.reddit.com/r/funny/comments/18pz3k1/my_dog_loves_the_snow/ket5r8q/',
            '',
            '# Add your comment URLs below',
        ]
    }
    
    df = pd.DataFrame(data)
    
    output_file = 'reddit_tracker_template.csv'
    df.to_csv(output_file, index=False)
    
    print(f"✅ CSV template created: {output_file}")

if __name__ == '__main__':
    print("Creating template files...\n")
    create_template()
    print()
    create_csv_template()
    print("\n✅ Templates ready to use!")