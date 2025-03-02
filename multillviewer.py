import os
import sys
import xml.sax
import PySimpleGUI as sg
import platform
if platform.uname()[0] == "Windows":
    # Windows only, to address blurry fonts
    from ctypes import windll
    windll.shcore.SetProcessDpiAwareness(1)
#elif platform.uname()[0] == "Linux":
#    name = "linux.so"
import textwrap

class SaxHandler(xml.sax.ContentHandler):
    def startDocument(self):
        pass

    def startElement(self, name, attrs):
        global langName, langCode, langDescription, langPublisher, langProv, lemmas, senses, synsets
        self.inDefinition = False
        
        if name == "Lexicon":
            langName.append( attrs.getValue("label"))
            langCode.append( attrs.getValue("language"))
            langDescription.append( attrs.getValue("dc:description"))
            langPublisher.append( attrs.getValue("dc:publisher"))
            langProv.append( attrs.getValue("dc:source").split("; "))
        elif name == "Lemma":
            self.currentLemma = attrs.getValue("writtenForm") 
            self.currentLemmaPos = attrs.getValue("partOfSpeech")
        elif name == "Sense":
            self.currentSense = attrs.getValue("id")
            word = {}
            word["senseId"] = self.currentSense
            word["synsetId"] = attrs.getValue("synset")
            word["pos"] = self.currentLemmaPos
            if self.currentLemma not in lemmas:
                lemmas[self.currentLemma] = []
            lemmas[self.currentLemma].append(word)
            sense = {}
            sense["word"] = self.currentLemma
            sense["pos"] = self.currentLemmaPos
            sense["synsetId"] = word["synsetId"]
            if word["senseId"] not in senses:
                senses[word["senseId"]] = sense
            else:
                senses[word["senseId"]]["word"] = sense["word"]
                senses[word["senseId"]]["pos"] = sense["pos"]
                senses[word["senseId"]]["synsetId"] = sense["synsetId"]
            if sense["synsetId"] not in synsets:
                synsets[sense["synsetId"]] = {}
                synsets[sense["synsetId"]]["lemmas"] = []

            if "status" in attrs.getNames():
                senses[word["senseId"]]["status"]=attrs.getValue("status")
                if  senses[word["senseId"]]["status"]!="deleted":
                    synsets[sense["synsetId"]]["lemmas"].append(self.currentLemma) 
            else:
                senses[word["senseId"]]["status"]="unmodified"
                synsets[sense["synsetId"]]["lemmas"].append(self.currentLemma)
            
            if word["synsetId"] not in synsets:
                synsets[word["synsetId"]]={}

            if "senses" not in synsets[word["synsetId"]]:
                synsets[word["synsetId"]]["senses"]=[]
            synsets[word["synsetId"]]["senses"].append(word["senseId"])

        elif name == "Synset":
            synset = {}
            synset["ili"] = attrs.getValue("ili")
            synset["lexicalized"] = attrs.getValue("lexicalized")
            
            synsetId = attrs.getValue("id")

            if synset["ili"][-1] != 'n' and synset["ili"][-1] !='v' and synset["ili"][-1] !='a' and synset["ili"][-1] !='r':
                if synset["ili"] in synsets:
                    synsets[synset["ili"]][langCode[len(langCode)-1]]=synsetId

            self.currentSynset = synsetId
            if synset["lexicalized"]=="true":
                synset["pos"] = attrs.getValue("partOfSpeech")
            if synsetId not in synsets:
                synsets[synsetId] = synset
            else:
                synsets[synsetId]["ili"] = synset["ili"]
                synsets[synsetId]["lexicalized"] = synset["lexicalized"]
                synsets[synsetId]["pos"] = synset["pos"]
        elif name == "Definition":
            synsets[self.currentSynset]["gloss"] = "[" + attrs.getValue("language") + "] "
            self.inDefinition = True
            # will add actuall gloss when we get to the PCDATA
        elif name == "SenseRelation":
            reltype = attrs.getValue("relType")
            target = attrs.getValue("target")
            if "relations" not in senses[self.currentSense]:
                senses[self.currentSense]["relations"] = {}
            if reltype not in senses[self.currentSense]["relations"]:
                senses[self.currentSense]["relations"][reltype] = []
            senses[self.currentSense]["relations"][reltype].append(target)
            # now add the inverse relation if applicable
            if reltype in inverseRelations:
                inverseSource = target
                inverseTarget = self.currentSense
                inverseReltype = inverseRelations[reltype]
                if inverseSource not in senses:
                    senses[inverseSource] = {}
                if "relations" not in senses[inverseSource]:
                    senses[inverseSource]["relations"] = {}
                if inverseReltype not in senses[inverseSource]["relations"]:
                    senses[inverseSource]["relations"][inverseReltype] = []
                senses[inverseSource]["relations"][inverseReltype].append(inverseTarget)
        elif name == "SynsetRelation":
            reltype = attrs.getValue("relType")
            target = attrs.getValue("target")
            if "relations" not in synsets[self.currentSynset]:
                synsets[self.currentSynset]["relations"] = {}
            if reltype not in synsets[self.currentSynset]["relations"]:
                synsets[self.currentSynset]["relations"][reltype] = []
            synsets[self.currentSynset]["relations"][reltype].append(target)
            # now add the inverse relation if applicable
            if reltype in inverseRelations:
                inverseSource = target
                inverseTarget = self.currentSynset
                inverseReltype = inverseRelations[reltype]
                if inverseSource not in synsets:
                    synsets[inverseSource] = {}
                if "relations" not in synsets[inverseSource]:
                    synsets[inverseSource]["relations"] = {}
                if inverseReltype not in synsets[inverseSource]["relations"]:
                    synsets[inverseSource]["relations"][inverseReltype] = []
                synsets[inverseSource]["relations"][inverseReltype].append(inverseTarget)

    def endElement(self, name):
        pass

    def characters(self, content):
        if self.inDefinition:
            synsets[self.currentSynset]["gloss"] = synsets[self.currentSynset]["gloss"] + content.strip()

def POS_DISPLAY(pos):
    return SText("(" + pos + ") ", font="Helvetica 12", text_color="red")

def GLOSS_DISPLAY(gloss):
    return SText(gloss, font="Helvetica 12")


def Collapsible(layout, key, title='', arrows=("–", "+"), collapsed=False):
    """
    User Defined Element
    A "collapsable section" element. Like a container element that can be collapsed and brought back
    :param layout:Tuple[List[sg.Element]]: The layout for the section
    :param key:Any: Key used to make this section visible / invisible
    :param title:str: Title to show next to arrow
    :param arrows:Tuple[str, str]: The strings to use to show the section is (Open, Closed).
    :param collapsed:bool: If True, then the section begins in a collapsed state
    :return:sg.Column: Column including the arrows, title and the layout that is pinned
    """
    global linkList
    linkList.append(key + "-BUTTON-")
    linkList.append(key + "-TITLE-")
    return sg.Column([[sg.T("          " + (arrows[1] if collapsed else arrows[0]), enable_events=True, k=key+'-BUTTON-', font="Helvetica 14 bold"),
                       sg.T(title, font="Helvetica 12 italic", enable_events=True, key=key+'-TITLE-')],
                      [sg.pin(sg.Column(layout, key=key, visible=not collapsed, metadata=arrows))]], pad=(0,0))

def SText(text, *positionalArgs, **keywordArgs):
    return sg.InputText(text, *positionalArgs, **keywordArgs, size=(len(text)+1, None),  pad=0, use_readonly_for_disable=True, disabled=True, disabled_readonly_background_color="white", border_width=0)

# def SText(text, *positionalArgs, **keywordArgs):
#     return sg.Text(text, *positionalArgs, **keywordArgs,  pad=0, border_width=0)


def LText(text, k, *positionalArgs, **keywordArgs):
    global linkList
    linkList.append(k)
    return [sg.Text("►", key=k, enable_events = True, pad=0, border_width=0, font="Helvetica 12 bold", text_color="blue"), SText(text, *positionalArgs, **keywordArgs)]

def resource_path(relative_path):
    base_path = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(base_path, relative_path)

# return unique value(s) for new object id(s) and update file based on how many new objects will be created
def id_next(obj, increase):
    filein=open("obj_ids.txt","r")
    fileout=open("obj_ids_tmp.txt","w")

    buffer=filein.readline()
    while(buffer!=""):
        if obj==buffer.split("-")[0]:
            ret=int(buffer.split("-")[1])
            
            fileout.write(obj+"-"+str(ret+increase)+"\n")
        else:
            fileout.write(buffer)
        
        buffer=filein.readline()
    
    filein.close()
    fileout.close()

    os.remove("obj_ids.txt")
    os.rename("obj_ids_tmp.txt","obj_ids.txt")

    return ret

# add sense: new_sense to synset :syn_id modifying file: file; will also add the sense and relative information to the data on the stack\in memory
def add_sense(new_sense, syn_id, file):

    word_lang=syn_id.split("-")[0]
    word_pos=synsets[syn_id]["pos"]
    filein=open(file,"r",encoding="utf8")
    fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
    buffer=filein.readline()

    current_language=""
    found_lexical_entry=False
    while(buffer!=""):
            
        if "<Lexicon " in buffer:
            current_language=buffer.strip().split(" ")[3].split("\"")[1]
            if current_language==word_lang:
                lexicon_start=filein.tell()

        if "writtenForm=\""+new_sense+"\"" in buffer and current_language==word_lang and buffer.split("partOfSpeech=\"")[1][0]==word_pos:
                    
            fileout.write(buffer)

            buffer=filein.readline()

            found_deleted=False
            while buffer!= "    </LexicalEntry>\n":

                if "synset=\""+syn_id+"\"" and "status=\"deleted\"" in buffer:

                    fileout.write(buffer.split("status=\"deleted\"")[0] + "status=\"new\"" + buffer.split("status=\"deleted\"")[1])

                    sense_id=buffer.split("id=\"")[1].split("\"")[0]
                    senses[sense_id]["status"]="new"
                    synsets[syn_id]["lemmas"].append(new_sense)

                    found_deleted=True
                    found_lexical_entry=True
                    break
                else:
                    fileout.write(buffer)
                
                buffer=filein.readline()

            if not found_deleted:
                new_id=id_next("sen",1)
                fileout.write("      <Sense id=\""+word_lang+"-sennew"+str(new_id)+"\" synset=\""+syn_id+"\" status=\"new\"></Sense>\n")
                found_lexical_entry=True

                new_id=word_lang+"-sennew"+str(new_id)
                sense={}
                sense["word"]=new_sense
                sense["pos"]=word_pos
                sense["synsetId"]=syn_id
                senses[str(new_id)]=sense

                synsets[syn_id]["lemmas"].append(new_sense)
                synsets[syn_id]["senses"].append(new_id)

                fileout.write(buffer)

        else:
            fileout.write(buffer)

        buffer=filein.readline()

    if not found_lexical_entry:
        filein.seek(lexicon_start)
        fileout.seek(lexicon_start)
        fileout.truncate()

        new_idw=id_next("wor",1)
        fileout.write("    <LexicalEntry id=\""+word_lang+"-word-"+word_pos+"new"+str(new_idw)+"\" status=\"new\">\n")
        fileout.write("      <Lemma writtenForm=\""+new_sense+"\" partOfSpeech=\""+word_pos+"\"></Lemma>\n")
        new_ids=id_next("sen",1)
        fileout.write("      <Sense id=\""+word_lang+"-sennew"+str(new_ids)+"\" synset=\""+syn_id+"\" status=\"new\"></Sense>\n")
        fileout.write("    </LexicalEntry>\n")
            
        buffer=filein.readline()
        while(buffer!=""):
            fileout.write(buffer)
            buffer=filein.readline()

        new_ids=word_lang+"-sennew"+str(new_ids)
        word={}
        word["senseId"] = new_ids
        word["synsetId"] = syn_id
        word["pos"] = word_pos

        lemmas[new_sense]=[word]

        sense={}
        sense["word"]=new_sense
        sense["pos"]=word_pos
        sense["synsetId"]=syn_id
        sense["status"]="new"
        senses[str(new_ids)]=sense

        synsets[syn_id]["lemmas"].append(new_sense)
        synsets[syn_id]["senses"].append(new_ids)

    filein.close()
    fileout.close()

    os.remove(file)
    os.rename(file[:-4]+"_tmp.xml",file)

    return 0

# ==================================================================================

WINDOW_TITLE = 'LiveLanguage Lexicon View'
posNames = {"n": "Noun", "v": "Verb", "a": "Adjective", "r": "Adverb"}
inverseRelations = {"hyponym": "hypernym", "hypernym": "hyponym", "mero_part": "holo_part", "holo_part": "mero_part", "mero_substance": "holo_substance", "holo_substance": "mero_substance", "mero_member": "holo_member", "holo_member": "mero_member", "subevent": "is_subevent_of", "is_subevent_of": "subevent", "attribute": "attribute", "metaphorically_related_concept": "metaphorically_related_concept", "metonymically_related_concept": "metonymically_related_concept", "is_aspect_of": "has_aspect", "has_aspect": "is_aspect_of", "metonym": "metonym", "cognate": "cognate", "derivation": "derivation", "antonym": "antonym", "also": "also", "similar": "similar"}
bias = (0, 0)
lemmas = {}
senses = {}
synsets = {}
relations = {}
langName = []
langCode = []
langPublisher = []
langDescription = []
langProv = []


if len(sys.argv) < 2:
    print("An LMF/XML file is needed as input argument! Exiting.")
    sys.exit(1)

file = sys.argv[1]

fn = open(file, encoding="utf8")
parser = xml.sax.make_parser()
handler = SaxHandler()
parser.setContentHandler(handler)
parser.parse(fn) # TODO: validation
fn.close()


if len(langName)==0:
    print("No Lexicon found in input file, Exiting")
    sys.exit(1)

sg.change_look_and_feel('LightGrey1')

if not os.path.exists("obj_ids.txt"):
    fileout=open("obj_ids.txt","w")
    fileout.write("syn-0\nsen-0\nwor-0\nili-0\n")
    fileout.close()

layoutTop = [
                [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(langName, key="-Selected language-")],
                [sg.Text('Word to search for:', font='Helvetica 12'), sg.InputText(key="wordinput", font='Helvetica 12',focus = True), sg.Button('Search Lexicon', bind_return_key = True)],
                [sg.Column([], key="content")]
            ]
Lexicon_info_combo=sg.Combo(langName,enable_events=True,readonly=True,key="Lexicon_info")
layoutBottom = [sg.Text("Lexicon info:",font="Verdana 10"),Lexicon_info_combo,sg.Push(),sg.Button('Quit')]

#section1 = [[sg.Input('Input sec 1', key='-IN1-')]]

layout = [ layoutTop,
           [sg.Text(key='-OUTPUT-', font='Helvetica 14 bold')],
           [sg.VPush()],
           layoutBottom,
           #[Collapsible(section1, SEC1_KEY,  'Section 1', collapsed=True)]
         ]
            
window = sg.Window('LiveLanguage Lexicon View', layout, resizable = True,finalize=True)
window.maximize()
# Event Loop to process "events" and get the "values" of the inputs
while True:
    linkList = []
    
    event, values = window.read()
    if event == sg.WIN_CLOSED or event == 'Quit': # if user closes window or clicks cancel
        break
    elif event == "Lexicon_info":
        i=langName.index(values["Lexicon_info"])
        sg.popup_scrolled(langName[i] + ' LiveLanguage Lexicon [' + langCode[i] + ']', "", "Description: " + langDescription[i], "", "Publisher: " + langPublisher[i], "", "Data sources:\n" + " - " + "\n - ".join(langProv[i]), title="Lexicon Info")
        continue
    elif event.startswith("LEMMA"):
        wordPostfix = event.split(":")[1]
        word = wordPostfix.split("_")[0] # remove postfix "_" and synset ID
    elif event.startswith("COLLAPSE_"):
        if event.endswith('-BUTTON-'):
            key = event[:-8]
        elif event.endswith('-TITLE-'):
            key = event[:-7]
        else:
            key = event
        window[key].update(visible=not window[key].visible)
        window[key + "-BUTTON-"].update("          " + (window[key].metadata[0] if window[key].visible else window[key].metadata[1]))

        contentSize = window["content"].get_size()
        newContentSize = (contentSize[0], contentSize[1] + 200)
        window["content"].set_size(newContentSize)

        # index=key.index('|')
        # column_key="column_" + key[9:index]

        # contentSize = window[column_key].get_size()
        # newContentSize = (contentSize[0], contentSize[1] + 200)
        # window[column_key].set_size(newContentSize)

        continue
    # synset-entry buttons
    elif event.startswith("Correct_gloss_"):

        splite=event[len("Correct_gloss_"):].split("_")
        if len(splite)==1:
            syn_id=splite[0]
        else:
            syn_id=splite[1]

        new_gloss = sg.popup_get_text("Insert gloss",default_text=synsets[syn_id]["gloss"].split("] ")[1])
        gloss_lang=synsets[syn_id]["gloss"].split("] ")[0]+"] "

        if new_gloss!=None:

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
            buffer=filein.readline()
            while(buffer!=""):
            
                if "Synset id=\"" + syn_id + "\"" in buffer:
                
                    fileouttmp=open("tmp","w")
                
                    if not "status=\"" in buffer:
                        fileouttmp.write(buffer[0:-2] + " status=\"modified\">\n")
                        fileout.write(buffer[0:-2] + " status=\"modified\">\n")
                    #elif " status=\"unmodified\"" in buffer:
                    else:
                        fileouttmp.write(buffer)
                        fileout.write(buffer)

                    buffer=filein.readline()

                    fileouttmp.write(buffer.split(">")[0]+ ">" + new_gloss + "</Definition>\n")
                    fileout.write(buffer.split(">")[0]+ ">" + new_gloss + "</Definition>\n")
                
                
                    fileouttmp.close()
                else:
                    fileout.write(buffer)
                    
                buffer=filein.readline()

            filein.close()
            fileout.close()
            synsets[syn_id]["gloss"]=gloss_lang + new_gloss

            os.remove(file)
            os.rename(file[:-4]+"_tmp.xml",file)
        
        else:
            continue
        
    elif event.startswith("Remove_sense_from_synset_"):
        
        splite=event[len("Remove_sense_from_synset_"):].split("_")

        if len(splite)==1:
            syn_id=splite[0]
        else:
            syn_id=splite[1]
        
        remove_sense_layout=[[sg.Text("Select which synonym to remove")]]

        row=[]
        for sense in synsets[syn_id]["senses"]:

            if senses[sense]["status"]!="deleted":
                row.append(sg.Button(senses[sense]["word"],key=sense))

        remove_sense_layout.append(row)

        remove_sense_window=sg.Window("Remove synonym", remove_sense_layout)

        r_s_event, r_s_values = remove_sense_window.read()

        if(r_s_event!=None):

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

            buffer=filein.readline()

            while buffer!="":

                if "<Sense id=\"" + r_s_event + "\"" in buffer:

                    # fileouttmp=open("tmp","w",encoding="utf8")

                    if "status=\"" in buffer:
                        fileout.write(buffer.split("status=\"")[0] + "status=\"deleted\"" + buffer.split("status=\"")[1].split("\"")[1])
                    else:
                        splitb=buffer.split("\">")
                        fileout.write(splitb[0] + "\" status=\"deleted\">" + splitb[1])

                    # fileouttmp.close()
                else:
                    fileout.write(buffer)
                
                buffer=filein.readline()

            senses[r_s_event]["status"]="deleted"
            synsets[syn_id]["lemmas"].remove(senses[r_s_event]["word"])

            filein.close()
            fileout.close()

            os.remove(file)
            os.rename(file[:-4]+"_tmp.xml",file)
        else:
            continue

        remove_sense_window.close()

    elif event.startswith("Add_sense_to_synset_"):

        splite=event[len("Add_sense_to_synset_"):].split("_")

        if len(splite)==1:
            syn_id=splite[0]
        else:
            syn_id=splite[1]

        new_sense=sg.popup_get_text("Insert new Synonym")

        unique=True
        for sense in synsets[syn_id]["senses"]:

            if senses[sense]["word"]==new_sense and senses[sense]["status"]!="deleted":
                unique=False
                break
        
        if new_sense!=None and unique:

            ret_val=add_sense(new_sense, syn_id, file)
        

    # deprecated
    # elif event.startswith("Correct_sense_of_synset_"):

    #     splite=event[len("Correct_sense_of_synset_"):].split("_")

    #     if len(splite)==1:
    #         syn_id=splite[0]
    #     else:
    #         syn_id=splite[1]

    #     correct_sense_layout=[[sg.Text("Select which synonym to correct")]]
    #     row=[]
    #     for sense in synsets[syn_id]["senses"]:
    #         if senses[sense]["status"]!="deleted":
    #             row.append(sg.Button(senses[sense]["word"],key=sense))

    #     correct_sense_layout.append(row)

    #     correct_sense_window=sg.Window("Correct synonym", correct_sense_layout)

    #     c_s_event, c_s_values = correct_sense_window.read()

    #     correct_sense_window.close()

    #     if c_s_event!=None:
    #         corrected_sense=sg.popup_get_text("Correct synonym: "+senses[c_s_event]["word"], default_text = senses[c_s_event]["word"])
    #     else: continue

    #     unique=True
    #     for sense in synsets[syn_id]["senses"]:

    #         if senses[sense]["word"]==corrected_sense and senses[sense]["status"]!="deleted":
    #             unique=False
    #             break

    #     if corrected_sense!=None and corrected_sense!=c_s_event and unique:

    #         filein=open(file,"r",encoding="utf8")
    #         fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
    #         word_lang=syn_id.split("-")[0]
    #         word_pos=synsets[syn_id]["pos"]

    #         buffer=filein.readline()
            
    #         while buffer!="":

    #             if "<Lexicon " in buffer:
    #                 current_language=buffer.strip().split(" ")[3].split("\"")[1]
    #                 fileout.write(buffer)

    #                 if current_language==word_lang:
    #                     lexicon_start=filein.tell()

    #                     buffer=filein.readline()
    #                     found_Lexical_Entry=False
    #                     sense_block=""
    #                     while not "</Lexicon>" in buffer:
                            
    #                         if (not found_Lexical_Entry) and "writtenForm=\""+corrected_sense+"\"" in buffer and buffer.split("partOfSpeech=\"")[1][0]==word_pos:

    #                             found_Lexical_Entry=True
    #                         elif "id=\"" + c_s_event + "\"" in buffer:
                                
    #                             if "status=\"" in buffer:
    #                                 if buffer.split("status=\"")[1].split("\"")[0]!="new":
    #                                     buffer=buffer.split("status=\"")[0] + "status=\"modified\"" + buffer.split("status=\"")[1].split("\"")[1]
    #                             else:
    #                                 buffer=buffer.split("\">")[0] + "\" status=\"modified\">" + buffer.split("\">")[1]

    #                             while buffer!="":

    #                                 if "</Sense>" in buffer:
    #                                     sense_block+=buffer
    #                                     break
    #                                 else:
    #                                     sense_block+=buffer

    #                                 buffer=filein.readline()
                            
    #                         buffer=filein.readline()
                        
    #                     filein.seek(lexicon_start)

    #                     if found_Lexical_Entry:
                            
    #                         buffer=filein.readline()
    #                         while buffer!="":

    #                             if "writtenForm=\""+corrected_sense+"\"" in buffer and buffer.split("partOfSpeech=\"")[1][0]==word_pos:
    #                                 fileout.write(buffer)
    #                                 fileout.write(sense_block)
    #                                 break
    #                             elif "id=\"" + c_s_event + "\"" in buffer:

    #                                 while buffer!="":
    #                                     if "</Sense>" in buffer:
    #                                         break
    #                                 buffer=filein.readline()
    #                             else:
    #                                 fileout.write(buffer)

    #                             buffer=filein.readline()

    #                     else:
    #                         new_idw=id_next("wor",1)
    #                         fileout.write("    <LexicalEntry id=\""+word_lang+"-word-"+synsets[syn_id]["pos"]+"new"+str(new_idw)+"\" status=\"new\">\n")
    #                         fileout.write("      <Lemma writtenForm=\""+ corrected_sense +"\" partOfSpeech=\""+ synsets[syn_id]["pos"] +"\"></Lemma>\n")
    #                         fileout.write(sense_block)
    #                         fileout.write("    </LexicalEntry>\n")

    #                         buffer=filein.readline()
    #                         while buffer!="":
    #                             if "id=\"" + c_s_event + "\"" in buffer:

    #                                 while buffer!="":
    #                                     if "</Sense>" in buffer:
    #                                         break
    #                                 buffer=filein.readline()
    #                             else:
    #                                 fileout.write(buffer)

    #                             buffer=filein.readline()

    #             else:
    #                 fileout.write(buffer)

    #             buffer=filein.readline()

    #         filein.close()
    #         fileout.close()

    #         oldsense=senses[c_s_event]["word"]

    #         senses[c_s_event]["word"]==corrected_sense
    #         if senses[c_s_event]["status"]!="new":
    #             senses[c_s_event]["status"]="modified"

    #         synsets[syn_id]["lemmas"].remove(oldsense)
    #         synsets[syn_id]["lemmas"].append(corrected_sense)

    #         for worddict in lemmas[oldsense]:
    #             if worddict["senseId"]==c_s_event:
    #                 lemmas[oldsense].remove(worddict) 
    #                 if len(lemmas[oldsense])==0:
    #                     lemmas.pop(oldsense)
            
    #         worddict={}

    #         worddict["senseId"]=c_s_event
    #         worddict["synsetId"]=syn_id
    #         worddict["pos"]=word_pos

    #         if not corrected_sense in lemmas:
    #             lemmas[corrected_sense]=[]
    #         lemmas[corrected_sense].append(worddict)

            # os.remove(file)
            # os.rename(file[:-4]+"_tmp.xml",file)
            
        # else: 
        #     continue

    elif event.startswith("Delexicalize_"):
        syn_id=event[len("Delexicalize_"):].split("_")[1]
        
        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        buffer=filein.readline()

        while(buffer!=""):
            
            if "<Synset id=\""+syn_id+"\"" in buffer:
                # fileouttmp=open("tmp","w",encoding="utf8")
                buffer=buffer.split("lexicalized=\"true\"")[0]+"lexicalized=\"false\""+buffer.split("lexicalized=\"true\"")[1]
                # fileouttmp.close()
                if not "status=\"" in buffer:
                    fileout.write(buffer[0:-2] + " status=\"modified\">\n")
                    #elif " status=\"unmodified\"" in buffer:
                else:
                    fileout.write(buffer)

            else:
                fileout.write(buffer)

            buffer=filein.readline()
        
        synsets[syn_id]["lexicalized"]="false"

        filein.close()
        fileout.close()

        os.remove(file)
        os.rename(file[:-4]+"_tmp.xml",file)

    #missing translation buttons
    elif event.startswith("Add_lexical_gap_"):
        syn_id=event[len("Add_lexical_gap_"):].split("_")[0]
        target_lang=event[len("Add_lexical_gap_"):].split("_")[1]
        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        target_ili=""
        if syn_id.split("-")[0]==langCode[0]:
            target_ili=syn_id
        else:
            target_ili=synsets[syn_id]["ili"]

        buffer=filein.readline()

        target_lexicon=False
        while buffer!="":
            if not target_lexicon and "<Lexicon " in buffer and buffer.strip().split(" ")[3].split("\"")[1]==target_lang:
                target_lexicon=True

            if target_lexicon and "</Lexicon>" in buffer:
                #fileouttmp=open("tmp","w",encoding="utf8")

                # to be completed
                #new_id=id_next("syn", 1)
                fileout.write("    <Synset id=\""+ target_lang +"-gap-"+ langCode[0] +"new" + "tmp" + "\" ili=\""+ target_ili +"\" lexicalized=\"false\" status=\"new\"></Synset>\n")
                fileout.write(buffer)

                #fileouttmp.close()
                target_lexicon=False
            else:
                fileout.write(buffer)
            buffer=filein.readline()


        filein.close()
        fileout.close()

        # os.remove(file)
        # os.rename(file[:-4]+"_tmp.xml",file)

    elif event.startswith("Add_synset_translation_"):

        entry_id=event[len("Add_synset_translation_"):].split("_")[0]
        syn_id=event[len("Add_synset_translation_"):].split("_")[1]

        if "relations" in synsets[entry_id]:
            print(synsets[entry_id]["relations"])

            for synreltype in synsets[entry_id]["relations"]:

                target_code=syn_id.split("-")[0]
                source_code=entry_id.split("-")[0]

                print(synreltype)

                middle_term=""
                final_term=""
                for synrel in synsets[entry_id]["relations"][synreltype]:
                    print(synrel)

                if source_code!=langCode[0]:
                    middle_term=synsets[synrel["ili"]]
                else:
                    middle_term=synrel

                if target_code!=langCode[0]:
                    if target_code in synsets[middle_term]:
                        final_term=synsets[middle_term][target_code]
                else:
                    final_term=middle_term

                if final_term!="":
                    print("something")

        # to be completed


    # untranslatable buttons
    elif event.startswith("Untranslatable_info_"):
        sg.popup("A concept is untranslatable if there is no way to translate it without using a description", title="What does untranslatable mean?")
        continue

    elif event.startswith("Lexicalize_synset_"):

        syn_id=event[len("Lexicalize_synset_"):].split("_")[1]
        source_id=event[len("Lexicalize_synset_"):].split("_")[0]

        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
        
        buffer=filein.readline()

        while buffer!="":

            if "Synset id=\"" + syn_id + "\"" in buffer:

                if "pos" not in  synsets[syn_id]:
                    synsets[syn_id]["pos"]=synsets[source_id]["pos"]               

                if "gloss" not in synsets[syn_id]:
                    synsets[syn_id]["gloss"]=sg.popup_get_text("Insert gloss")

                if not "senses" in synsets[syn_id]:
                    new_sense=sg.popup_get_text("Insert word")

            buffer=filein.readline()

        filein.close()
        fileout.close()

        # to be completed

    else:
        word = values["wordinput"].strip()

    # TODO: escape dangerous characters
    word = word.replace('"', '')
    
    if word not in lemmas and not word == "":
        window["-OUTPUT-"].update('“' + word + '” not found!')
        continue
    contentByPos = {}
    window.set_cursor("watch")
    if word == "":
        pass
    else:
        for wordAttrs in lemmas[word]:
            sense = senses[wordAttrs["senseId"]]
            pos = sense["pos"]
            relsByType = {}
            # find all sense relations
            if "relations" in sense:
                senseRelations = sense["relations"] 
                for reltype in senseRelations: 
                    for target in senseRelations[reltype]: 
                        targetSense = senses[target] 
                        if reltype not in relsByType: 
                            relsByType[reltype] = [] 
                        relsByType[reltype].append(targetSense)
            synsetId = sense["synsetId"]
            if not synsetId:
                print(word + " not found.")
                sys.exit(0)
            synset = synsets[synsetId]
            if "relations" in synset:
                synRelations = synset["relations"]
                for reltype in synRelations:
                    for target in synRelations[reltype]:
                        targetSynset = synsets[target]
                        if reltype not in relsByType:
                            relsByType[reltype] = []
                        relsByType[reltype].append(targetSynset)

            if synsets[synsetId]["lexicalized"]=="true":
                if pos not in contentByPos:
                    contentByPos[pos] = []
                content = {}
                content["gloss"] = synset["gloss"]
                content["relations"] = relsByType
                content["synsetId"] = synsetId
                content["lemmas"] = synsets[synsetId]["lemmas"]
                contentByPos[pos].append(content)
    layoutBody = []

    for pos in contentByPos:
        layoutBody.append([sg.Text(posNames[pos], font='Helvetica 12 bold')])

        for entry in contentByPos[pos]:

            layoutRow = []
            entry_layout=[[]]
            translated_layoutRow=[]
            translated_layout=[[]]

            lemmaList = ", ".join(entry["lemmas"])
            lemmaList.strip()

            wraplength=(window.size[0]/(2*11))
            if wraplength<5:
                wraplength=5

            for line in textwrap.wrap(lemmaList, wraplength):
                layoutRow = []
                layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
                entry_layout.append(layoutRow)

            #debug
            # if layoutRow[0].Size[0]>len(lemmaList)+1:
            #     layoutRow.append(GLOSS_DISPLAY("b"))
            # layoutRow.append(GLOSS_DISPLAY("a"))
            
            wraplength=int(window.size[0]/(2*10)-14)
            if wraplength<5:
                wraplength=5

            for line in textwrap.wrap(entry["gloss"],wraplength):
                
                layoutRow = []
                layoutRow.append(GLOSS_DISPLAY(line))
                entry_layout.append(layoutRow)


            untranslatable=False
            missing_translation=False
            tranlation_present=False
            same_language=False
            translated_synsetId=""
            target_code=""
            if not values["-Selected language-"] not in langName:

                synset_language=langName[0]
                middle_term=""
                if synsets[entry["synsetId"]]["ili"][-1] == 'n' or synsets[entry["synsetId"]]["ili"][-1] =='v' or synsets[entry["synsetId"]]["ili"][-1] =='a' or synsets[entry["synsetId"]]["ili"][-1] =='r':
                    middle_term=entry["synsetId"]
                else:
                    i=0
                    while True:
                        if entry["synsetId"][i]=='-':
                            break
                        i+=1

                    for code in langCode:
                        if entry["synsetId"][0:i]==code:
                            j=langCode.index(code)
                            synset_language=langName[j]
                            break
                        
                    middle_term=synsets[entry["synsetId"]]["ili"]
                if synset_language==values["-Selected language-"]:

                    same_language=True

                else:
                    
                    if values["-Selected language-"]==langName[0]:
                        translated_synsetId=middle_term
                        target_code=langCode[0]
                    else:
                        j=langName.index(values["-Selected language-"])
                        target_code=langCode[j]

                        if target_code in synsets[middle_term]:
                            translated_synsetId=synsets[middle_term][target_code]
                        else:
                            missing_translation=True

                    if translated_synsetId != "":
                        if  "lemmas" in synsets[translated_synsetId] and synsets[translated_synsetId]["lexicalized"]=="true":

                            translated_lemmaList=", ".join(synsets[translated_synsetId]["lemmas"])

                            wraplength=(window.size[0]/(2*11))
                            if wraplength<5:
                                wraplength=5

                            for line in textwrap.wrap(translated_lemmaList, wraplength):
                                translated_layoutRow = []
                                translated_layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
                                translated_layout.append(translated_layoutRow)


                            wraplength=int(window.size[0]/(2*10))
                            if wraplength<5:
                                wraplength=5
                            
                            for line in textwrap.wrap(synsets[translated_synsetId]["gloss"],wraplength):
                            
                                translated_layoutRow = []
                                translated_layoutRow.append(GLOSS_DISPLAY(line))
                                translated_layout.append(translated_layoutRow)

                            tranlation_present=True

                            if "relations" in synsets[translated_synsetId]:
                                # print("synset_relations: "+str(synsets[translated_synsetId]["relations"]))

                                for relation_type in synsets[translated_synsetId]["relations"]:

                                    collapsableSection=[]
                                    for relation_target in synsets[translated_synsetId]["relations"][relation_type]:
                                        
                                        if synsets[relation_target]["lexicalized"]=="true":
                                            collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                            lemmaList = synsets[relation_target]["lemmas"]
                                            initial_row_size=len("              ")
                                        
                                            for lemma in lemmaList:
                                                initial_row_size+=(len(lemma)+3)
                                            
                                                lemmaKey = "LEMMA:" + lemma + "_" + translated_synsetId + "_" + entry["synsetId"]
                                                collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                        
                                            gloss = synsets[relation_target]["gloss"]


                                            if initial_row_size > window.size[0]/(5*10):
                                                wraplength=int((window.size[0]/(2*10)) - len("              "))

                                                collapsableSection.append(collapsableRow)
                                                for line in textwrap.wrap(gloss, wraplength):
                                                    collapsableRow = []
                                                    collapsableRow.append(GLOSS_DISPLAY("              " + "  " + line))
                                                    collapsableSection.append(collapsableRow)

                                            else:    
                                                wraplength=int(window.size[0]/(2*10))-(initial_row_size)-2
                                                if wraplength<5:
                                                    wraplength=5

                                                first=True
                                                for line in textwrap.wrap(gloss, wraplength):
                                                    if first==False:
                                                        collapsableRow = []
                                                        collapsableRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
                                                    first=False
                                                    collapsableRow.append(GLOSS_DISPLAY(line))
                                                    collapsableSection.append(collapsableRow)
                                    if collapsableSection!=[]:
                                        collapsableSectionKey = "COLLAPSE_" + translated_synsetId + "_" + entry["synsetId"] + "|" + relation_type
                                        translated_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations", arrows=("–", "+"), collapsed = True)])

                            if "senses" in synsets[translated_synsetId]:

                                for sense in synsets[translated_synsetId]["senses"]:
                                    #print("synset_senses: "+sense)
                                    if "relations" in senses[sense] and senses[sense]["status"]!="deleted":
                                        for relation_type in senses[sense]["relations"]:
                                            #print(relation_type+str(senses[sense]["relations"][relation_type]))
                                            collapsableSection=[]

                                            for relation_target in senses[sense]["relations"][relation_type]:

                                                # print(relation_target)
                                                # print("translatedsynsetId: "+translated_synsetId)
                                                if senses[relation_target]["status"]!="deleted":
                                                    collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                                    lemma=senses[relation_target]["word"]
                                                    lemmaKey = "LEMMA:" + lemma + "_" + relation_target + "_" + sense + "_" + translated_synsetId + "_" + entry["synsetId"]
                                                    collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                                    gloss = synsets[senses[relation_target]["synsetId"]]["gloss"]

                                                    wraplength=int(window.size[0]/(2*10))-len("              " + lemma)-1
                                                    if wraplength<5:
                                                        wraplength=5

                                                    first=True
                                                    for line in textwrap.wrap(gloss, wraplength):
                                                        if first==False:
                                                            collapsableRow = []
                                                            collapsableRow.append(GLOSS_DISPLAY(' '*(len(lemma + "              ")-3)))
                
                                                        first=False
                                                        collapsableRow.append(GLOSS_DISPLAY(line))
                                                        collapsableSection.append(collapsableRow)
                                            
                                            if collapsableSection!=[]:
                                                collapsableSectionKey = "COLLAPSE_" + translated_synsetId + "_" + entry["synsetId"] + "|" + relation_type + sense
                                                translated_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations for " + senses[sense]["word"], arrows=("–", "+"), collapsed = True)])
                            
                        else:
                            
                            # print("Not lexicalized, ",translated_synsetId)
                            untranslatable=True
            
            
            if "relations" in synsets[entry["synsetId"]]:
                # print("synset_relations: "+str(synsets[entry["synsetId"]]["relations"]))

                for relation_type in synsets[entry["synsetId"]]["relations"]:

                    collapsableSection=[]
                    for relation_target in synsets[entry["synsetId"]]["relations"][relation_type]:
                        
                        if synsets[relation_target]["lexicalized"]=="true":
                            collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                            lemmaList = synsets[relation_target]["lemmas"]
                            initial_row_size=len("              ")
                                        
                            for lemma in lemmaList:
                                initial_row_size+=(len(lemma)+3)
                                            
                                lemmaKey = "LEMMA:" + lemma + "_" + entry["synsetId"]
                                collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')

                            gloss = synsets[relation_target]["gloss"]

                            if initial_row_size > window.size[0]/(5*10):
                                wraplength=int((window.size[0]/(2*11)) - len("              ")-10)

                                collapsableSection.append(collapsableRow)
                                for line in textwrap.wrap(gloss, wraplength):
                                    collapsableRow = []
                                    collapsableRow.append(GLOSS_DISPLAY("              " + "  " + line))
                                    collapsableSection.append(collapsableRow)

                            else:    
                                wraplength=int(window.size[0]/(2*11))-(initial_row_size)-6
                                if wraplength<5:
                                    wraplength=5

                                first=True
                                for line in textwrap.wrap(gloss, wraplength):
                                    if first==False:
                                        collapsableRow = []
                                        collapsableRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
                                    first=False
                                    collapsableRow.append(GLOSS_DISPLAY(line))
                                    collapsableSection.append(collapsableRow)
                    if collapsableSection!=[]:
                        collapsableSectionKey = "COLLAPSE_" + "_" + entry["synsetId"] + "|" + relation_type
                        entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations", arrows=("–", "+"), collapsed = True)])

            if "senses" in synsets[entry["synsetId"]]:

                for sense in synsets[entry["synsetId"]]["senses"]:
                    # print("synset_sense: " + senses[sense]["word"] + " - " + sense)
                    if "relations" in senses[sense] and senses[sense]["status"]!="deleted":
                        for relation_type in senses[sense]["relations"]:
                            # print(relation_type+str(senses[sense]["relations"][relation_type]))
                            collapsableSection=[]

                            for relation_target in senses[sense]["relations"][relation_type]:

                                # print(relation_target)
                                # print("translatedsynsetId: "+translated_synsetId)
                                if senses[relation_target]["status"]!="deleted":       
                                    collapsableRow=[sg.Text("              ", font="Helvetica 12 bold")]
                                    lemma=senses[relation_target]["word"]
                                    lemmaKey = "LEMMA:" + lemma + "_" + relation_target + "_" + sense + "_" + entry["synsetId"]
                                    collapsableRow = collapsableRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')
                                    gloss = synsets[senses[relation_target]["synsetId"]]["gloss"]

                                    wraplength=int(window.size[0]/(2*11))-len("              " + lemma)-10
                                    if wraplength<5:
                                        wraplength=5

                                    first=True
                                    for line in textwrap.wrap(gloss, wraplength):
                                        if first==False:
                                            collapsableRow = []
                                            collapsableRow.append(GLOSS_DISPLAY(' '*(len(lemma + "              ")-3)))
    
                                        first=False
                                        collapsableRow.append(GLOSS_DISPLAY(line))
                                        collapsableSection.append(collapsableRow)
                            if collapsableSection!=[]:              
                                collapsableSectionKey = "COLLAPSE_" + entry["synsetId"] + "|" + relation_type + sense
                                entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + relation_type + " relations for " + senses[sense]["word"], arrows=("–", "+"), collapsed = True)])
            # if entry["relations"]:
            #     for reltype in entry["relations"]:
            #         collapsableSection = []
            #         for rel in entry["relations"][reltype]:
            #             layoutRow = [sg.Text("              ", font="Helvetica 12 bold")]

            #             initial_row_size=len("              ")

            #             if "lemmas" in rel:
            #                 # it is a synset relation
            #                 lemmaList = rel["lemmas"]
            #             else:
            #                 # it is a sense relation
            #                 lemmaList = [rel["word"]] # only one word for a sense relation!
            #             for lemma in lemmaList:

            #                 if initial_row_size+len(lemma)+3 > window.size[0]/(2.3*10)-10:

            #                     collapsableSection.append(layoutRow)
            #                     layoutRow=[]
            #                     layoutRow.append(sg.Text("              ", font="Helvetica 12 bold"))
            #                     initial_row_size=len("              ")

            #                 initial_row_size+=len(lemma)+3
            #                 lemmaKey = "LEMMA:" + lemma + "_" + entry["synsetId"]
            #                 layoutRow = layoutRow + LText(lemma, lemmaKey, enable_events = True, font='Helvetica 12 bold', text_color='blue')

                            

            #             if "gloss" in rel:
            #                 # it is a synset relation
            #                 gloss = rel["gloss"]
            #             else:
            #                 # it is a sense relation
            #                 gloss = synsets[rel["synsetId"]]["gloss"]

            #             if initial_row_size > window.size[0]/(5*10):

            #                 wraplength=int((window.size[0]/(2*10)) - len("              ")-14)
            #                 if wraplength<5:
            #                     wraplength=5

            #                 collapsableSection.append(layoutRow)
            #                 for line in textwrap.wrap(gloss, wraplength):
            #                     layoutRow = []
            #                     layoutRow.append(GLOSS_DISPLAY("              " + "  " + line))
            #                     collapsableSection.append(layoutRow)

            #             else:    
            #                 wraplength=int(window.size[0]/(2*11))-(initial_row_size+14)
            #                 if wraplength<5:
            #                     wraplength=5

            #                 first=True
            #                 for line in textwrap.wrap(gloss, wraplength):
            #                     if first==False:
            #                         layoutRow = []
            #                         layoutRow.append(GLOSS_DISPLAY(' '*(initial_row_size-6)))
                
            #                     first=False
            #                     layoutRow.append(GLOSS_DISPLAY(line))
            #                     collapsableSection.append(layoutRow)

            #         collapsableSectionKey = "COLLAPSE_" + entry["synsetId"] + "|" + reltype
            #         entry_layout.append([Collapsible(collapsableSection, collapsableSectionKey, title=" " + reltype + " relations", arrows=("–", "+"), collapsed = True)])
    
            translated_column_key=""
            if untranslatable:

                Untranslatable_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + translated_synsetId, pad=((0,3),(3,3)))
                translated_layout.append([sg.Text("Untranslatable", font="Helvetica 12"), Untranslatable_info])
                
                Lexical_gap_button=sg.Button("Add word", key="Lexicalize_synset_" + entry["synsetId"] + "_" + translated_synsetId)

                translated_layout.append([Lexical_gap_button])
            elif missing_translation:

                translated_layout.append([sg.Text("Missing translation", font="Helvetica 12")])
                
                Missing_translation_button=sg.Button("Add translation", key="Add_synset_translation_" + entry["synsetId"] + "_" + target_code)
                Add_lexical_gap_button=sg.Button("Add lexical gap",key="Add_lexical_gap_" + entry["synsetId"] + "_" + target_code, pad=((3,0),(3,3)))
                Lexical_gap_info=sg.Button("ℹ", key="Lexical_gap_info_" + entry["synsetId"] + "_" + target_code, pad=((0,3),(3,3)))

                translated_layout.append([Missing_translation_button, Add_lexical_gap_button, Lexical_gap_info])
            elif not (same_language or not tranlation_present):

                #Correction_button_translation=sg.Button("Correct word", key="Correct_sense_of_synset_" + entry["synsetId"] + "_" + translated_synsetId)
                Gloss_correction_button_tranlslation=sg.Button("Correct gloss", key="Correct_gloss_" + entry["synsetId"] + "_" + translated_synsetId)
                Add_synonym_button_translation=sg.Button("Add synonym", key="Add_sense_to_synset_" + entry["synsetId"] + "_" + translated_synsetId)
                buttonrow=[Gloss_correction_button_tranlslation, Add_synonym_button_translation]
                if  len(synsets[translated_synsetId]["lemmas"])>1:
                    Remove_synonym_button_translation=sg.Button("Remove synonym", key="Remove_sense_from_synset_" + entry["synsetId"] + "_" + translated_synsetId)
                    buttonrow.append(Remove_synonym_button_translation)
                To_lexical_gap_button=sg.Button("Change to lexical gap", key="Delexicalize_" + entry["synsetId"] + "_" + translated_synsetId)
                buttonrow.append(To_lexical_gap_button)
                translated_layout.append(buttonrow)

            
            #Correction_button=sg.Button("Correct word", key="Correct_sense_of_synset_" + entry["synsetId"])
            Gloss_correction_button=sg.Button("Correct gloss", key="Correct_gloss_" + entry["synsetId"])
            Add_synonym_button=sg.Button("Add synonym", key="Add_sense_to_synset_" + entry["synsetId"])
            buttonrow=[Gloss_correction_button, Add_synonym_button]
            if  len(synsets[entry["synsetId"]]["lemmas"])>1:
                Remove_synonym_button=sg.Button("Remove synonym", key="Remove_sense_from_synset_" + entry["synsetId"])
                buttonrow.append(Remove_synonym_button)
            entry_layout.append(buttonrow)
            
            if translated_synsetId!="":
                translated_column_key="column_"+translated_synsetId+"_"+entry["synsetId"]

            translated_column=sg.Column(translated_layout, key = translated_column_key, vertical_alignment="top", pad=((0,0),(3,10)))
            
            entry_layout.append([sg.Sizer(window.size[0]/2 + 6, 0)])
            entry_column=sg.Column(entry_layout, key="column_" + entry["synsetId"], vertical_alignment="top", pad=((0,0),(3,10)))
            
            total_column=[entry_column]
            total_column.append(translated_column)
            layoutBody.append(total_column)
                    

    layoutBody = [sg.Column(layoutBody, scrollable = True, key="content", expand_x = True, expand_y = True,vertical_scroll_only=True)] # size=window["content"].Size
    
    Lexicon_info_combo=sg.Combo(langName,enable_events=True,readonly=True,key="Lexicon_info")
    layoutBottom = [sg.Text("Lexicon info:",font="Verdana 10"),Lexicon_info_combo,sg.Push(),sg.Button('Quit')]
    newLayout = [
                 [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(langName, key="-Selected language-",default_value=values["-Selected language-"])],
                 [sg.Text('Word to search for:', font='Helvetica 12'), sg.InputText(key="wordinput", font='Helvetica 12', focus=True), sg.Button('Search Lexicon', bind_return_key = True)], 
                 [sg.Text(key='-OUTPUT-', font='Helvetica 14 bold')],
                 layoutBody,
                 layoutBottom
                ]
    currentLocation = window.CurrentLocation()
    adjustedLocation = (currentLocation[0] - bias[0], currentLocation[1] - bias[1])
    newWindow = sg.Window(WINDOW_TITLE, newLayout, location = adjustedLocation, resizable = True, finalize = True)
    newWindow.size = window.size
    newLocation = newWindow.CurrentLocation()
    if not newLocation == currentLocation:
        # window is migrating due to titlebar size: compensate it
        bias = (newLocation[0] - currentLocation[0], newLocation[1] - currentLocation[1])
    window.close()
    window = newWindow
    window["wordinput"].update(word)
    for linkKey in linkList:
        
        window[linkKey].set_cursor("hand2")
    window.set_cursor("arrow")
    window["-OUTPUT-"].update('“' + word + '”')

window.close()