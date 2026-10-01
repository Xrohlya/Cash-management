# Мой мир

Игра Mini App без сборщика. Все финансовые операции остаются в существующем API.

## Файлы

- app.js: события, загрузка игры, действия и подтверждаемое пополнение накоплений.
- view.js: отрисовка игрового состояния и финансовой сводки.
- store.js: состояние игрового интерфейса.
- animation.js и motion.css: дыхание, покачивание, прыжок и реакция на касание.
- design.css: только оформление игры и сетка пяти верхних вкладок.
- evolution.js: предметы второго и третьего этапов комнат.
- decorations.js: приобретаемые игровые предметы.
- images/: пять прозрачных PNG персонажей.
- rooms/: пять независимых SVG комнат.

## Правила

Комнаты растут при 3000 и 18000 опыта; каждые 50 опыта повышают уровень.
Дальше открываются главы каждые 18000 опыта. Размер постепенно растет до
60000 опыта и ограничен, чтобы не закрывать интерфейс. Пять возрастных обликов
каждого питомца находятся в images/{pet}-ages.png: атлас 3x2, пять ячеек
в порядке чтения, шестая пустая. appearance.js/appearance.css отвечают
за отображение и выбор цветовой палитры; возрастные правила в
services/pet_appearance.py. Цвет хранится в отдельной игровой таблице.
Настройки открываются
шестеренкой. Экономика и долгосрочный план описаны в DEVELOPMENT.md.
Новые изображения созданы встроенным image_gen с исходными питомцами как
референсами; спецификация и возрастные различия в ART_PROMPTS.md.
Опыт и монеты общие при переключении питомца. Игра никогда сама не списывает
реальные деньги. Покупки украшений и награды не меняют финансовые таблицы.
Кнопка накоплений требует подтверждения реальной учетной операции.
Косметические награды за посещение, ведение учета и накопления выдаются
не более одного раза за день на миссию, независимо от числа операций и их сумм.
Миссии не штрафуют пользователя и не стимулируют увеличение расходов.

## Изображения

Созданы встроенным image_gen, с реальным прозрачным фоном. Исходный общий промпт:

Use case: stylized-concept. Asset type: single transparent game character sprite
for a financial companion mobile game. Premium cozy 3D clay toy illustration,
soft rounded forms, slightly three-quarter front view, full body centered and
completely visible, lively friendly expression, crisp detailed silhouette.
Consistent soft studio light with subtle cyan rim lighting. Transparent background,
no ground plane, no environment, no text, no logos, no watermarks. Square image
with comfortable transparent margins. One character only, suitable for CSS
breathing and bouncing animation.

Subjects:

- robot.png: friendly small rounded silver robot with cyan eyes, articulated arms, copper accents.
- cat.png: cute fluffy tuxedo cat with mint eyes, small pink nose, sitting with a curled tail.
- dragon.png: baby emerald dragon with amber horns, tiny wings and a curled tail.
- penguin.png: cute little penguin with navy feathers, white belly, yellow feet and a turquoise scarf.
- owl.png: baby tawny owl with huge amber eyes, cream face, feather tufts and little wings.

Иллюстрации не являются покадровыми спрайтами: движение реализовано CSS-
трансформациями всего персонажа. Анимация не воспроизводится в скрытом разделе
и отключается через reduced-motion или переключатель пользователя.
