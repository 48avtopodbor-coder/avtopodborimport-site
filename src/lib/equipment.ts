type EquipmentItem = { label: string; status: "Штатно" | "Опция" };
type EquipmentGroup = { title: string; items: EquipmentItem[] };

const groups: { title: string; sections: string[]; names: Record<string, string> }[] = [
  {
    title: "Безопасность",
    sections: ["被动安全", "主动安全"],
    names: {
      ABS防抱死: "Антиблокировочная система ABS",
      "制动力分配(EBD/CBC等)": "Распределение тормозных усилий",
      "刹车辅助(EBA/BAS/BA等)": "Помощь при экстренном торможении",
      "牵引力控制(ASR/TCS/TRC等)": "Противобуксовочная система",
      "车身稳定控制(ESC/ESP/DSC等)": "Система стабилизации",
      ISOFIX儿童座椅接口: "Крепления детских кресел ISOFIX",
      车道偏离预警系统: "Предупреждение о выезде из полосы",
      "主动刹车/主动安全系统": "Автоматическое экстренное торможение",
      疲劳驾驶提示: "Контроль усталости водителя",
      前方碰撞预警: "Предупреждение о столкновении",
      道路救援呼叫: "Вызов помощи на дороге",
    },
  },
  {
    title: "Комфорт и управление",
    sections: ["驾驶操控", "驾驶功能", "外观/防盗", "天窗/玻璃", "空调/冰箱"],
    names: {
      发动机启停技术: "Система старт-стоп",
      自动驻车: "Автоматическое удержание автомобиля",
      上坡辅助: "Помощь при трогании на подъёме",
      辅助泊车入位: "Помощь при парковке",
      并线辅助: "Контроль слепых зон",
      电动后备厢: "Электропривод багажника",
      感应后备厢: "Бесконтактное открывание багажника",
      电动后备厢位置记忆: "Память положения двери багажника",
      无钥匙启动系统: "Запуск двигателя без ключа",
      车窗一键升降功能: "Автоматический режим стеклоподъёмников",
      车窗防夹手功能: "Защита от защемления стеклоподъёмников",
      后雨刷: "Задний стеклоочиститель",
      后排独立空调: "Отдельный климат-контроль заднего ряда",
      后座出风口: "Воздуховоды для задних пассажиров",
      温度分区控制: "Раздельное управление температурой",
      "车内PM2.5过滤装置": "Фильтр мелких частиц PM2.5",
    },
  },
  {
    title: "Салон",
    sections: ["方向盘/内后视镜", "座椅配置"],
    names: {
      多功能方向盘: "Многофункциональный руль",
      方向盘换挡拨片: "Подрулевые переключатели передач",
      方向盘加热: "Обогрев руля",
      全液晶仪表盘: "Цифровая приборная панель",
      HUD抬头数字显示: "Проекционный дисплей",
      运动风格座椅: "Спортивные сиденья",
      后排杯架: "Подстаканники для задних пассажиров",
    },
  },
  {
    title: "Мультимедиа",
    sections: ["互联/智能化", "车内充电"],
    names: {
      "蓝牙/车载电话": "Bluetooth и громкая связь",
      应用商店: "Магазин приложений",
      车联网: "Подключение автомобиля к интернету",
      "Wi-Fi热点": "Точка доступа Wi-Fi",
    },
  },
];

export function modelEquipment(raw: unknown): EquipmentGroup[] {
  let data: unknown = raw;
  if (typeof raw === "string") {
    try {
      data = JSON.parse(raw);
    } catch {
      return [];
    }
  }
  if (!Array.isArray(data)) return [];

  return groups
    .map(({ title, sections, names }) => {
      const items: EquipmentItem[] = [];
      for (const section of data) {
        if (
          !Array.isArray(section) ||
          !sections.includes(section[0]) ||
          !Array.isArray(section[1])
        ) {
          continue;
        }
        for (const item of section[1]) {
          if (!Array.isArray(item) || typeof item[0] !== "string" || typeof item[1] !== "string")
            continue;
          const label = names[item[0]];
          const value = item[1].trim();
          if (label && (value === "●" || value === "○")) {
            items.push({ label, status: value === "●" ? "Штатно" : "Опция" });
          }
        }
      }
      return { title, items };
    })
    .filter(({ items }) => items.length > 0);
}
