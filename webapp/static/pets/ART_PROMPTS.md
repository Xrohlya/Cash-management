# Возрастные атласы

Созданы встроенным image_gen, прозрачный фон включен. Исходные
images/{pet}.png переданы как референсы идентичности и стиля. Исходники
сохранены, новые файлы images/{pet}-ages.png не заменяют старые изображения.

Общая спецификация промптов: stylized-concept; transparent PNG game sprite
atlas, landscape 1536x1024; equal 3 columns x 2 rows square cells; five
distinct anatomical age models, polished 3D toy game illustration; reading
order baby / teen / young / adult / legend; bottom right empty transparent.
Whole character front three-quarter idle, centered in each cell, feet at
88% cell height, requested maximum height 76% and transparent margins 12%.
No labels, grid, scenery, floor, backdrop or background haze. True alpha
transparency outside characters. Different anatomy and details, not resizes.

Возрастные различия по каждому промпту:

- Robot: silver, copper, cyan eyes; baby round huge head/stubby body;
  teen longer limbs/juvenile antenna; young slim/agile/upgraded joints;
  adult sturdy/larger torso; legend ornate advanced armor/luminous circuits.
- Cat: black-white fur, green eyes, white paws/chest; baby round kitten;
  teen lanky/long legs; young agile; adult fluffy/mature; legend long fur,
  luminous cyan collar and silvery ornamental tufts.
- Dragon: green scales, gold horns, pale belly; baby horn buds/tiny wings;
  teen lanky/growing wings; young patterned scales; adult broad/developed
  wings; legend elaborate horns, teal scale markings and armored crest.
- Penguin: navy-white, turquoise scarf; baby round downy chick;
  teen molting juvenile; young sleek/long scarf; adult broad flippers;
  legend emperor golden ear patches/embroidered luminous scarf/icy crest.
- Owl: warm brown-cream, golden eyes; baby round downy owlet; teen new
  feathers; young developed ear tufts; adult broad chest/layered wings;
  legend silver-gold feathers/luminous cyan tips/celestial crest.

Рендер показывает одну ячейку атласа без изменения самих bitmap-файлов.
Палитры реализованы CSS-фильтрами; это не отдельные перекрашенные арты.
