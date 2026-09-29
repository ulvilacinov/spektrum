/**
 * Static grammar reference shown in the "Dilbilgisi" modal.
 *
 * Text markup: parts in [brackets] are highlighted (endings, articles), e.g. "d[em]".
 */

export interface GrammarTable {
  caption: string
  columns: string[]
  rows: { label: string; cells: string[] }[]
  /** Colour the four columns as masculine / feminine / neuter / plural. */
  genders?: boolean
  note?: string
}

export type GrammarBlock =
  | ({ kind: 'table' } & GrammarTable)
  | { kind: 'list'; title: string; items: string[] }
  | { kind: 'tip'; title: string; text: string[] }

export interface GrammarSection {
  id: string
  emoji: string
  title: string
  intro: string
  blocks: GrammarBlock[]
}

const CASES = ['Nominativ', 'Akkusativ', 'Dativ', 'Genitiv']
const GENDERS = ['Eril (der)', 'Dişil (die)', 'Nötr (das)', 'Çoğul (die)']

function byCase(cells: string[][]): GrammarTable['rows'] {
  return cells.map((row, index) => ({ label: CASES[index], cells: row }))
}

export const GRAMMAR: GrammarSection[] = [
  {
    id: 'cases',
    emoji: '🧭',
    title: 'Haller',
    intro:
      'Almancada isim, artikel, sıfat ve zamir cümledeki görevine göre dört halden birine girer. ' +
      'Hali çoğunlukla artikelin sonundan anlarsın.',
    blocks: [
      {
        kind: 'table',
        caption: 'Dört hal',
        columns: ['Soru', 'Görevi', 'Türkçede', 'Örnek'],
        rows: [
          {
            label: 'Nominativ',
            cells: ['Wer? Was?', 'Özne', 'Yalın hal: adam', '[Der] Mann kommt.'],
          },
          {
            label: 'Akkusativ',
            cells: ['Wen? Was?', 'Doğrudan nesne', 'Belirtme hali: adamı', 'Ich sehe [den] Mann.'],
          },
          {
            label: 'Dativ',
            cells: ['Wem?', 'Dolaylı nesne', 'Yönelme hali: adama', 'Ich helfe [dem] Mann.'],
          },
          {
            label: 'Genitiv',
            cells: ['Wessen?', 'Sahiplik', 'Tamlayan hali: adamın', 'das Auto [des] Mann[es]'],
          },
        ],
      },
      {
        kind: 'tip',
        title: 'Türkçe benzetmesi her zaman tutmaz',
        text: [
          'Edatlar ve bazı fiiller hali kendileri belirler (bkz. Edatlar).',
          '„fragen“ Akkusativ ister: Ich frage [dich]. (sana soruyorum, ama Almancada „seni“)',
          'Konuşma dilinde Genitiv yerine çoğu zaman von + Dativ kullanılır: das Auto [vom] Mann (von dem Mann).',
        ],
      },
      {
        kind: 'list',
        title: 'Dativ isteyen sık fiiller',
        items: [
          'helfen (yardım etmek): Ich helfe [dir].',
          'danken (teşekkür etmek): Ich danke [Ihnen].',
          'gefallen (hoşuna gitmek): Das gefällt [mir].',
          'gehören (ait olmak): Das Buch gehört [mir].',
          'antworten (cevap vermek), gratulieren (tebrik etmek), schmecken (tadı hoşa gitmek), passen (uymak)',
        ],
      },
      {
        kind: 'list',
        title: 'İki nesneli fiiller: kişi Dativ, şey Akkusativ',
        items: [
          'Ich gebe [dem] Kind [den] Ball. (çocuğa topu veriyorum)',
          'geben, schenken, zeigen, erklären, schicken, bringen, kaufen',
        ],
      },
      {
        kind: 'list',
        title: 'İsmin kendisi de değişir',
        items: [
          'Dativ çoğulda isme -n eklenir: mit den Kinder[n] (isim zaten -n / -s ile bitmiyorsa)',
          'Genitivde eril ve nötr isimler -s / -es alır: des Mann[es], des Auto[s]',
          'Bazı eril isimler (n-Deklination) Nominativ dışında -(e)n alır: den Student[en], dem Kollege[n]',
        ],
      },
    ],
  },
  {
    id: 'articles',
    emoji: '📘',
    title: 'Artikeller',
    intro: 'der / die / das ve ein / kein / mein, hale göre sonlarını değiştirir.',
    blocks: [
      {
        kind: 'table',
        caption: 'Belirli artikel: der, die, das',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['d[er]', 'd[ie]', 'd[as]', 'd[ie]'],
          ['d[en]', 'd[ie]', 'd[as]', 'd[ie]'],
          ['d[em]', 'd[er]', 'd[em]', 'd[en] +n'],
          ['d[es] +s', 'd[er]', 'd[es] +s', 'd[er]'],
        ]),
        note: 'dieser, jeder, welcher, jener de aynı sonları alır (das → dies[es]).',
      },
      {
        kind: 'table',
        caption: 'Belirsiz artikel: ein, eine',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['ein', 'ein[e]', 'ein', '–'],
          ['ein[en]', 'ein[e]', 'ein', '–'],
          ['ein[em]', 'ein[er]', 'ein[em]', '–'],
          ['ein[es]', 'ein[er]', 'ein[es]', '–'],
        ]),
        note: 'Çoğulun belirsiz artikeli yoktur: Ich habe Kinder.',
      },
      {
        kind: 'table',
        caption: 'kein ve iyelik: mein, dein, sein, ihr, unser, euer, Ihr',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['kein', 'kein[e]', 'kein', 'kein[e]'],
          ['kein[en]', 'kein[e]', 'kein', 'kein[e]'],
          ['kein[em]', 'kein[er]', 'kein[em]', 'kein[en]'],
          ['kein[es]', 'kein[er]', 'kein[es]', 'kein[er]'],
        ]),
        note: 'euer ek alınca e düşer: eur[e], eur[en]. Örnek: mit mein[em] Bruder, für unser[e] Kinder.',
      },
      {
        kind: 'tip',
        title: 'Sonu olmayan üç yer',
        text: [
          'ein / kein / mein üç yerde ek almaz: eril Nominativ, nötr Nominativ ve nötr Akkusativ.',
          'Tam bu yerlerde cinsiyet işaretini sıfat taşır: ein neu[er] Tisch, ein neu[es] Haus (bkz. Sıfatlar).',
        ],
      },
    ],
  },
  {
    id: 'adjectives',
    emoji: '🎨',
    title: 'Sıfatlar',
    intro:
      'İsmin önündeki sıfat, önündeki artikele göre çekimlenir. İsimden sonra (sein ile) ' +
      'çekimlenmez: Das Haus ist neu.',
    blocks: [
      {
        kind: 'tip',
        title: '„eine neues Haus“ mu?',
        text: [
          '❌ eine neues Haus: Haus nötr (das), bu yüzden artikel ein olur, eine değil.',
          '✅ ein neu[es] Haus: ein cinsiyeti göstermediği için -es işaretini sıfat taşır.',
          '✅ das neu[e] Haus: burada das zaten gösteriyor, sıfat sadece -e alır.',
          'Altın kural: Artikel sonu gösteriyorsa sıfat -e / -en alır. Göstermiyorsa (ya da artikel yoksa) sonu sıfat taşır.',
        ],
      },
      {
        kind: 'table',
        caption: '1) der, dieser, jeder … sonrası',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['-[e]', '-[e]', '-[e]', '-[en]'],
          ['-[en]', '-[e]', '-[e]', '-[en]'],
          ['-[en]', '-[en]', '-[en]', '-[en]'],
          ['-[en]', '-[en]', '-[en]', '-[en]'],
        ]),
        note: 'der neu[e] Tisch · Ich kaufe den neu[en] Tisch. · mit der neu[en] Lampe · in den neu[en] Häusern',
      },
      {
        kind: 'table',
        caption: '2) ein, kein, mein … sonrası',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['-[er]', '-[e]', '-[es]', '-[en]'],
          ['-[en]', '-[e]', '-[es]', '-[en]'],
          ['-[en]', '-[en]', '-[en]', '-[en]'],
          ['-[en]', '-[en]', '-[en]', '-[en]'],
        ]),
        note: 'ein neu[er] Tisch · ein neu[es] Haus · Ich kaufe einen neu[en] Tisch. · mit einer neu[en] Lampe · keine neu[en] Häuser',
      },
      {
        kind: 'table',
        caption: '3) Artikel yoksa',
        columns: GENDERS,
        genders: true,
        rows: byCase([
          ['-[er]', '-[e]', '-[es]', '-[e]'],
          ['-[en]', '-[e]', '-[es]', '-[e]'],
          ['-[em]', '-[er]', '-[em]', '-[en]'],
          ['-[en]', '-[er]', '-[en]', '-[er]'],
        ]),
        note: 'kalt[er] Kaffee · kalt[e] Milch · kalt[es] Wasser · mit kalt[em] Wasser · kalt[e] Getränke. Sonlar belirli artikelin sonlarıyla neredeyse aynı (dem → kalt[em]).',
      },
    ],
  },
  {
    id: 'pronouns',
    emoji: '🙋',
    title: 'Zamirler',
    intro: 'Şahıs zamirleri de hale göre değişir.',
    blocks: [
      {
        kind: 'table',
        caption: 'Şahıs zamirleri',
        columns: ['Nominativ', 'Akkusativ', 'Dativ'],
        rows: [
          { label: 'ben', cells: ['ich', 'mich', 'mir'] },
          { label: 'sen', cells: ['du', 'dich', 'dir'] },
          { label: 'o (eril)', cells: ['er', 'ihn', 'ihm'] },
          { label: 'o (dişil)', cells: ['sie', 'sie', 'ihr'] },
          { label: 'o (nötr)', cells: ['es', 'es', 'ihm'] },
          { label: 'biz', cells: ['wir', 'uns', 'uns'] },
          { label: 'siz', cells: ['ihr', 'euch', 'euch'] },
          { label: 'onlar', cells: ['sie', 'sie', 'ihnen'] },
          { label: 'Siz (resmî)', cells: ['Sie', 'Sie', 'Ihnen'] },
        ],
      },
      {
        kind: 'list',
        title: 'Örnekler',
        items: [
          'Ich sehe [dich]. (seni görüyorum, Akkusativ)',
          'Ich helfe [dir]. (sana yardım ediyorum, Dativ)',
          'Das gefällt [mir]. (bu hoşuma gidiyor, Dativ)',
          'Kannst du [ihn] anrufen? (onu arayabilir misin?, Akkusativ)',
        ],
      },
    ],
  },
  {
    id: 'prepositions',
    emoji: '📍',
    title: 'Edatlar',
    intro: 'Her edat belirli bir hal ister. Edattan sonraki artikel o hale göre çekimlenir.',
    blocks: [
      {
        kind: 'table',
        caption: 'Edatlar ve halleri',
        columns: ['Edatlar', 'Örnek'],
        rows: [
          {
            label: 'Akkusativ',
            cells: ['durch, für, gegen, ohne, um, bis', 'Das ist für [den] Chef.'],
          },
          {
            label: 'Dativ',
            cells: [
              'aus, bei, mit, nach, seit, von, zu, gegenüber, ab',
              'Ich fahre mit [dem] Bus.',
            ],
          },
          {
            label: 'İki yönlü',
            cells: [
              'an, auf, hinter, in, neben, über, unter, vor, zwischen',
              'Wohin? → Akkusativ · Wo? → Dativ',
            ],
          },
          {
            label: 'Genitiv',
            cells: ['wegen, trotz, während, statt, innerhalb, außerhalb', 'wegen [des] Wetter[s]'],
          },
        ],
      },
      {
        kind: 'tip',
        title: 'İki yönlü edatlar: Wohin? mi Wo? mu?',
        text: [
          'Hareket, yön (nereye?) → Akkusativ: Ich lege das Buch auf [den] Tisch.',
          'Konum (nerede?) → Dativ: Das Buch liegt auf [dem] Tisch.',
          'Fiil çiftleri: legen / liegen, stellen / stehen, setzen / sitzen, hängen / hängen',
        ],
      },
      {
        kind: 'list',
        title: 'Kaynaşmalar',
        items: [
          'in + dem = [im] · in + das = [ins]',
          'an + dem = [am] · an + das = [ans]',
          'bei + dem = [beim] · von + dem = [vom]',
          'zu + dem = [zum] · zu + der = [zur]',
        ],
      },
    ],
  },
]
