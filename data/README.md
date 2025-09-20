# Organization Data

This directory contains the source data for the foundation's giving portfolio.

## Adding Organizations

Edit `organizations.csv` to add or update organizations. Each row represents one organization with the following columns:

### Required Columns

- **Org**: Organization name (required)
- **Class**: Giving scope - must be one of:
  - `Local` - Bay Area organizations
  - `National` - US-wide organizations
  - `Global` - International organizations
- **Reason**: Category of giving (lowercase), one of:
  - `education` - Education initiatives
  - `environment` - Environmental protection
  - `homeless` - Housing & homelessness
  - `church` - Faith-based organizations
  - `food` - Food security
  - `justice` - Social justice
  - `health` - Health & medical

### Optional Columns

- **Amount**: Dollar amount given (e.g., "$1,000")
- **Why**: Personal note about why you support this org
- **Summary**: Brief description of the organization
- **Website**: Organization website URL
- **EIN**: Employer Identification Number
- **CharityNavigator**: Charity Navigator profile URL
- **GuideStar**: GuideStar profile URL

## Example Row

```csv
Org,Amount,Reason,Class,Why,EIN,Website,CharityNavigator,GuideStar,Summary
Khan Academy,"$5,000",education,National,"Free world-class education for anyone anywhere",36-4641974,https://www.khanacademy.org,https://www.charitynavigator.org/ein/364641974,https://www.guidestar.org/profile/36-4641974,"Nonprofit providing free online educational resources and personalized learning tools for students worldwide."
```

## Building the Site

After editing the CSV, rebuild the site:

```bash
# From the project root
python build.py
```

The build script will:
1. Read this CSV file
2. Fetch favicons for each organization
3. Generate the portfolio table
4. Create the complete static site in `dist/`

## Tips

- Keep summaries concise (1-2 sentences)
- Include the full website URL with https://
- The "Why" field is for personal reflections on your giving
- Leave fields empty if data is not available
- Organizations are automatically sorted by Class (Local → National → Global)