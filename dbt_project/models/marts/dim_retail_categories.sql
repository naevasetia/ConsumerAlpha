SELECT * FROM (
    VALUES
        ('RSAFS',  'Total Retail & Food Services',    'Macro Benchmark',           'discount code'),
        ('RSGMS',  'General Merchandise Stores',      'Broadline Retail',           'clearance sale'),
        ('RSFHFS', 'Furniture & Home Furnishings',    'Big-Ticket Discretionary',  'furniture sale'),
        ('RSEAS',  'Electronics & Appliance Stores',  'Tech Discretionary',         'buy laptop'),
        ('RSDBS',  'Building Materials & Garden',     'Home Improvement',           'home renovation')
) AS t(category_code, category_name, sector_group, primary_search_keyword)