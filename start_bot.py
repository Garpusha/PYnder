import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
import db_function as dbf
from vk_search import Vk
import configparser


config = configparser.ConfigParser()  # создаём объекта парсера
config.read('config.ini')

my_pynder = dbf.PYnder_DB(rebuild=True)


access_token = config["VK_token"]["TOKEN"]
vk_session = vk_api.VkApi(token=access_token)
vk = vk_session.get_api()
longpoll = VkLongPoll(vk_session)


# функция вызова первой клавиатуры
def first_keyboards(id_, text):
    vk.messages.send(
        user_id=id_,
        message=text,
        random_id=0,
        keyboard=open("keyboards/first_button.json", "r", encoding="UTF-8").read(),
    )


# функция вызова второй клавиатуры
def all_buttons(id_, text, images_list):
    vk.messages.send(
        user_id=id_,
        message=text,
        attachment=images_list,
        random_id=0,
        keyboard=open("keyboards/all_buttons.json", "r", encoding="UTF-8").read(),
    )


def favorite_buttons(id_, text, images_list):
    vk.messages.send(
        user_id=id_,
        message=text,
        attachment=images_list,
        random_id=0,
        keyboard=open("keyboards/favorite_buttons.json", "r", encoding="UTF-8").read(),
    )


def sender(id_, text):
    vk.messages.send(user_id=id_, message=text, random_id=0)


def return_buttons(id_, text):
    vk.messages.send(
        user_id=id_,
        message=text,
        random_id=0,
        keyboard=open("keyboards/all_buttons.json", "r", encoding="UTF-8").read(),
    )


# логика бота
first_run = True
index = 0
mode = 0

for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:
        try:
            if event.to_me:
                if first_run:
                    first_run = False
                    my_id = event.user_id
                    vk_search = Vk(my_id)
                    my_data = vk_search.get_final_data()
                    print(len(my_data))  #(Саша) убрать в релизе
                msg = event.text.lower()
                my_msg = event.message

                match msg:
                    case "старт":
                        index = 0
                        sender(my_id, "Секунду, ищу варианты для тебя.\n")
                        my_pynder.add_owner(str(my_id))
                        my_data = vk_search.get_final_data()
                        sender(my_id, f"Найдено вариантов: {len(my_data)}.")
                        user_text, user_photo = vk_search.search_favorite(
                            index, my_data
                        )
                        all_buttons(my_id, user_text, user_photo)
                        # continue
                    case "назад":
                        if index == 0:
                            sender(my_id, "Это самая первая запись, предыдущих нет.\n")
                        else:
                            index -= 1
                            print(index)
                            user_text, user_photo = vk_search.search_favorite(
                                index, my_data
                            )
                            all_buttons(my_id, user_text, user_photo)
                            # continue
                    case "дальше":
                        if index == len(my_data) - 1:
                            # Тима, наверное здесь стоит сделать запрос новых записей если можно вытащить не первые 10,
                            # например, а вторые 10, потом третьи и т.д. (Саша)
                            sender(
                                my_id,
                                "Это последняя запись, выбирай из того что есть.\n",
                            )
                        else:
                            index += 1
                            print(index)
                            user_text, user_photo = vk_search.search_favorite(index, my_data)
                            all_buttons(my_id, user_text, user_photo)
                        # continue
                    case "добавить в избранное":
                        if my_pynder.add_favorite(my_data[index], str(my_id)):
                            sender(my_id, "Добавлено.\n")
                        else:
                            sender(my_id, "Уже добавлено.\n")
                    case "удалить из избранного":
                        if mode == 1:
                            delete_result = my_pynder.delete_favorite(my_data[index]["vk_id"], str(my_id))
                        elif mode == 2:
                            if len(favorite_dict) == 0:
                                delete_result = False
                            else:
                                delete_result = my_pynder.delete_favorite(favorite_dict[favorite_index]["vk_id"], str(my_id))

                        if delete_result:
                            sender(my_id, "Удалено.\n")
                            favorite_dict = my_pynder.get_favorite(str(my_id))
                            if len(favorite_dict) == 0:
                                sender(my_id, "В Избранном ничего нет.\n")
                                all_buttons(my_id, user_text, user_photo)
                            else:
                                if mode == 2:
                                    if favorite_index > len(favorite_dict) - 1:
                                        favorite_index = len(favorite_dict) - 1
                                    f_user_text, f_user_photo = vk_search.search_favorite(
                                        favorite_index, favorite_dict
                                    )
                                    favorite_buttons(my_id, f_user_text, f_user_photo)
                        else:
                            if mode == 1:
                                sender(my_id, "Не найдено.\n")
                            elif mode == 2:
                                sender(my_id, "В Избранном ничего нет.\n")
                                all_buttons(my_id, user_text, user_photo)
                    case "просмотреть избранное":
                        favorite_dict = my_pynder.get_favorite(str(my_id))
                        if len(favorite_dict) == 0:
                            sender(my_id, "В избранном ничего нет.\n")
                        else:
                            mode = 2    #Режим избранного
                            sender(my_id, "Захожу в Избранное.\n")
                            favorite_index = 0
                            sender(my_id, f"Записей в Избранном: {len(favorite_dict)}.\n")
                            f_user_text, f_user_photo = vk_search.search_favorite(
                                favorite_index, favorite_dict
                            )
                            favorite_buttons(my_id, f_user_text, f_user_photo)
                    case "вернуться в поиск":
                        sender(my_id, "Возвращаюсь в режим поиска. Ты остановился здесь:\n")
                        mode = 1 #Режим поиска
                        all_buttons(my_id, user_text, user_photo)
                    # Навигация в Избранном
                    case "следующий":
                        if len(favorite_dict) == 0:
                            sender(my_id, "В избранном ничего нет.\n")
                        else:
                            # сюда код для прохода по избранным вперед
                            if favorite_index == len(favorite_dict) - 1:
                                sender(my_id, "Это последняя запись в Избранном.\n")
                            elif favorite_index > len(favorite_dict) - 1:
                                #Это на случай реализации удаления внутри Избранного
                                favorite_index = len(favorite_dict) - 1
                                sender(my_id, "Это последняя запись в Избранном.\n")
                            else:
                                favorite_index += 1
                                f_user_text, f_user_photo = vk_search.search_favorite(
                                    favorite_index, favorite_dict
                                )
                                favorite_buttons(my_id, f_user_text, f_user_photo)
                    case "предыдущий":
                        if len(favorite_dict) == 0:
                            sender(my_id, "В избранном ничего нет.\n")
                        else:
                            if favorite_index == 0:
                                sender(my_id, "Это первая запись в Избранном.\n")
                            else:
                                favorite_index -= 1
                                f_user_text, f_user_photo = vk_search.search_favorite(
                                    favorite_index, favorite_dict
                                )
                                favorite_buttons(my_id, f_user_text, f_user_photo)
                    case "закончить поиск":
                        first_keyboards(my_id,"Пока(((\nЕсли хочешь снова искать,\n нажми на кнопку Старт.\n")


                    case _:
                        if len(msg) > 0:
                            mode = 1 #Режим поиска
                            first_keyboards(
                                my_id,
                                "Привет, я бот для поиска новых знакомств!\nНажми на кнопку Старт.\n"
                            )
        except Exception as ex:
            print(ex)
