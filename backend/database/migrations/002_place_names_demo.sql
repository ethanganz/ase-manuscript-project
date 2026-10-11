-- DEMO DATA ONLY. Attaches 4 places to random existing pages.
with new_places as (
  insert into public.places (name, country_code, lat, lng) values
    ('Geneva', 'CH', 46.2044, 6.1432),
    ('Zurich', 'CH', 47.3769, 8.5417),
    ('Paris',  'FR', 48.8566, 2.3522),
    ('Lyon',   'FR', 45.7640, 4.8357)
  returning id, name
)
insert into public.place_mentions (place_id, page_id, snippet)
select np.id, pg.id, 'arrived in ' || np.name || ' late in the evening'
from new_places np
cross join lateral (select id from public.pages order by random() limit 1) pg;

-- To remove the demo data later:
-- delete from public.places where name in ('Geneva','Zurich','Paris','Lyon');


-- to see 
-- select * from mention_details;