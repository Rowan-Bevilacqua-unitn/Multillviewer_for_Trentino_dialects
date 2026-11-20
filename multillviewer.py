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
import shutil

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
                if  not senses[word["senseId"]]["status"].startswith("deleted"):
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
                else:
                    synsets[synset["ili"]]={}
                    synsets[synset["ili"]][langCode[len(langCode)-1]]=synsetId

            self.currentSynset = synsetId
            if "partOfSpeech" in attrs.getNames():
                synset["pos"] = attrs.getValue("partOfSpeech")

            if synsetId not in synsets:
                synsets[synsetId] = synset
            else:
                synsets[synsetId]["ili"] = synset["ili"]
                synsets[synsetId]["lexicalized"] = synset["lexicalized"]
                if synset["lexicalized"]!="false":
                    synsets[synsetId]["pos"] = synset["pos"]

            if "status" in attrs.getNames():
                synsets[synsetId]["status"]=attrs.getValue("status")
            else:
                synsets[synsetId]["status"]="unmodified"
        elif name == "Definition":
            synsets[self.currentSynset]["gloss"] = "[" + attrs.getValue("language") + "] "
            self.inDefinition = True
            # will add actuall gloss when we get to the PCDATA

            if "status" in attrs.getNames():
                synsets[self.currentSynset]["gloss_status"]=attrs.getValue("status")
            else: synsets[self.currentSynset]["gloss_status"]="unmodified"
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

def GLOSS_DISPLAY(gloss, background_color=None):
    return SText(gloss, font="Helvetica 12", background_color=background_color)


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

# def SText(text, *positionalArgs, **keywordArgs):
#     return sg.InputText(text, *positionalArgs, **keywordArgs, size=(len(text)+1, None),  pad=0, use_readonly_for_disable=True, disabled=True, disabled_readonly_background_color="white", border_width=0)

def SText(text, background_color=None, *positionalArgs, **keywordArgs):
    return sg.Text(text, *positionalArgs, **keywordArgs,  pad=0, border_width=0, background_color=background_color)


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

                if "synset=\"" + syn_id + "\"" and "status=\"deleted" in buffer:
                    
                    new_status=""
                    if "status=\"deleted\"" in buffer:
                        fileout.write(buffer.split(" status=\"deleted\"")[0] + buffer.split(" status=\"deleted\"")[1])
                        new_status="unmodified"

                    if "status=\"deleted-again\"" in buffer:
                        fileout.write(buffer.split("status=\"deleted-again\"")[0] + "status=\"new\"" + buffer.split("status=\"deleted-again\"")[1])
                        new_status="new"

                    sense_id=buffer.split("id=\"")[1].split("\"")[0]
                    senses[sense_id]["status"]=new_status
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
                sense["status"]="new"
                senses[str(new_id)]=sense

                synsets[syn_id]["lemmas"].append(new_sense)
                synsets[syn_id]["senses"].append(new_id)

                word={}
                word["senseId"] = new_id
                word["synsetId"] = syn_id
                word["pos"] = word_pos

                if new_sense not in lemmas:
                    lemmas[new_sense]=[]
                lemmas[new_sense].append(word)

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

        if new_sense not in lemmas:
            lemmas[new_sense]=[]
        lemmas[new_sense].append(word)

        sense={}
        sense["word"]=new_sense
        sense["pos"]=word_pos
        sense["synsetId"]=syn_id
        sense["status"]="new"
        senses[str(new_ids)]=sense

        if not "lemmas" in synsets[syn_id]:
            synsets[syn_id]["lemmas"]=[]
        synsets[syn_id]["lemmas"].append(new_sense)
        if not "senses" in synsets[syn_id]:
            synsets[syn_id]["senses"]=[]
        synsets[syn_id]["senses"].append(new_ids)

    filein.close()
    fileout.close()

    os.remove(file)
    os.rename(file[:-4]+"_tmp.xml",file)

    return 0

# remove sense: r_senseId from synset :syn_id modifying file: file; also modifies the stack
def remove_sense(r_senseId, syn_id ,file):

    filein=open(file,"r",encoding="utf8")
    fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

    buffer=filein.readline()

    new_status=""
    while buffer!="":

        if "<Sense id=\"" + r_senseId + "\"" in buffer:

            # fileouttmp=open("tmp","w",encoding="utf8")

            if "status=\"new\"" in buffer:
                fileout.write(buffer.split("status=\"")[0] + "status=\"deleted-again\"" + buffer.split("status=\"")[1].split("\"")[1])
                new_status="deleted-again"
            else:
                splitb=buffer.split("\">")
                fileout.write(splitb[0] + "\" status=\"deleted\">" + splitb[1])
                new_status="deleted"

            # fileouttmp.close()
        else:
            fileout.write(buffer)
                
        buffer=filein.readline()

    senses[r_senseId]["status"]=new_status
    synsets[syn_id]["lemmas"].remove(senses[r_senseId]["word"])

    filein.close()
    fileout.close()

    os.remove(file)
    os.rename(file[:-4]+"_tmp.xml",file)

    return 0

# checks if there are any illegal characters in string
def has_illegal_characters(string):

    global illegal_charachters

    found=False
    for c in illegal_charachters:
        if c in string:
            found=True
            break

    return found

# standerdized popup
def illegal_characters_popup():
    sg.popup("Illegal character present\nIllegal characters: " + str(illegal_charachters),title="Error")
    return

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

illegal_charachters=['\"','=','<','>']

visualize_modifications=False

if len(sys.argv) < 2:
    print("An LMF/XML file is needed as input argument! Exiting.")
    sys.exit(1)

original_file = sys.argv[1]
file=original_file[:-4] + "_modified.xml"

path=os.path.dirname(os.path.abspath(sys.argv[0])) + "\\"

# create modified file if it doesn't exist
if not os.path.exists(file):
    shutil.copyfile(path + original_file, path + file)

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

#create obj_ids.txt if it doesn't exist
if not os.path.exists("obj_ids.txt"):
    fileout=open("obj_ids.txt","w")
    fileout.write("syn-0\nsen-0\nwor-0\nili-0\n")
    fileout.close()

lang_selection=langName.copy()
lang_selection.append("")

if visualize_modifications:
    vb_color="green"
else: vb_color="red"

#Top of the screen

layoutTop = [
                [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(lang_selection, key="-Selected language-"), sg.Button("Visualize modifications",key="-Visualize_modifications-", button_color=vb_color)],
                [sg.Text('Word to search for:', font='Helvetica 12'), sg.InputText(key="wordinput", font='Helvetica 12',focus = True), sg.Button('Search Lexicon', bind_return_key = True)],
                [sg.Column([], key="content")]
            ]

Lexicon_info_combo=sg.Combo(langName,enable_events=True,readonly=True,key="Lexicon_info")
layoutBottom = [sg.Text("Lexicon info:",font="Verdana 10"),Lexicon_info_combo,sg.Push(),sg.Button('Quit')]

#section1 = [[sg.Input('Input sec 1', key='-IN1-')]]

#The layout shown when the application is run

layout = [ layoutTop,
           [sg.Text(key='-OUTPUT-', font='Helvetica 14 bold')],
           [sg.VPush()],
           layoutBottom,
           #[Collapsible(section1, SEC1_KEY,  'Section 1', collapsed=True)]
         ]

word=""

window = sg.Window('MultiLiveLanguage Lexicon View', layout, resizable = True,finalize=True)
#fullscreen
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
    elif event.startswith("COLLAPSE_"): # toggle collapsable object
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

        continue

    # Visualise modifications Button

    elif(event.startswith("-Visualize_modifications-")):
        if visualize_modifications:
            visualize_modifications=False
        else: visualize_modifications=True

        word = values["wordinput"].strip()

    # synset-entry buttons ------------------------------------------------------------------------------------------------------------------------
    
    # modifies the gloss of a synset 
    elif event.startswith("Correct_gloss_"):

        splite=event[len("Correct_gloss_"):].split("_")
        if len(splite)==1:
            syn_id=splite[0]
        else:
            syn_id=splite[1]

        new_gloss = sg.popup_get_text("Insert gloss",default_text=synsets[syn_id]["gloss"].split("] ")[1])
        gloss_lang=synsets[syn_id]["gloss"].split("] ")[0]+"] "

        if new_gloss==None:
            continue
        
        new_gloss=new_gloss.strip()

        found=has_illegal_characters(new_gloss)

        if found:
            illegal_characters_popup()

        if not found:

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
            buffer=filein.readline()
            gloss_new_status=""
            while(buffer!=""):
            
                if "Synset id=\"" + syn_id + "\"" in buffer:
                
                
                    # if not "status=\"" in buffer:
                    #     fileout.write(buffer[0:-2] + " status=\"modified\">\n")
                    #elif " status=\"unmodified\"" in buffer:
                    # else:
                    fileout.write(buffer)

                    buffer=filein.readline()
                    
                    if "status=\"new\"" in buffer or "status=\"modified\"" in buffer:
                        fileout.write(buffer.split(">")[0]+ ">" + new_gloss + "</Definition>\n")
                    else:
                        fileout.write(buffer.split(">")[0]+ " status=\"modified\">" + new_gloss + "</Definition>\n")
                        gloss_new_status="modified"
                
                else:
                    fileout.write(buffer)
                    
                buffer=filein.readline()

            filein.close()
            fileout.close()
            synsets[syn_id]["gloss"]=gloss_lang + new_gloss
            if gloss_new_status!="":
                synsets[syn_id]["gloss_status"]="modified"

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

        #create window with list of senses to choose from 
        row=[]
        for sense in synsets[syn_id]["senses"]:
            if not senses[sense]["status"].startswith("deleted"):
                row.append(sg.Button(senses[sense]["word"],key=sense))

        remove_sense_layout.append(row)
        remove_sense_window=sg.Window("Remove synonym", remove_sense_layout)

        r_s_event, r_s_values = remove_sense_window.read()

        if(r_s_event!=None):

            remove_sense(r_s_event, syn_id, file)

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

        if new_sense==None:
            continue

        new_sense=new_sense.strip()

        unique=True
        for sense in synsets[syn_id]["senses"]:

            if senses[sense]["word"]==new_sense and  not senses[sense]["status"].startswith("deleted"):
                unique=False
                break

        found=has_illegal_characters(new_sense)

        if found:
            illegal_characters_popup()
        
        if  unique and not found:

            ret_val=add_sense(new_sense, syn_id, file)
        else:
            continue

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

    # set lexicalization of synset to false
    elif event.startswith("Delexicalize_"):
        syn_id=event[len("Delexicalize_"):].split("_")[1]
        
        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        buffer=filein.readline()

        while(buffer!=""):
            
            if "<Synset id=\""+syn_id+"\"" in buffer:

                lexical_value=synsets[syn_id]["lexicalized"]
                buffer=buffer.split("lexicalized=\"" + lexical_value + "\"")[0] + "lexicalized=\"false\"" + buffer.split("lexicalized=\"" + lexical_value + "\"")[1]

                if not "status=\"" in buffer:
                    fileout.write(buffer[0:-2] + " status=\"modified\">\n")
                    synsets[syn_id]["status"]="modified"
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

    # missing translation / no data buttons --------------------------------------------------------------------------------------------------------
    elif event.startswith("Set_nodata_to_untranslatable_"):

        source_id=event[len("Set_nodata_to_untranslatable_"):].split("_")[0]
        syn_lang=event[len("Set_nodata_to_untranslatable_"):].split("_")[1]

        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        new_ili=""
        if syn_lang==langCode[0]:
            new_ili="new" + str(id_next("ili",1)) + "-" + synsets[source_id]["pos"]
        else:
            if source_id.split("-")[0]==langCode[0]:
                new_ili=source_id
            else:
                new_ili=synsets[source_id]["ili"]

        buffer=filein.readline()

        new_id=""

        target_lexicon=False
        while buffer!="":
            if not target_lexicon and "<Lexicon " in buffer and buffer.strip().split(" ")[3].split("\"")[1]==syn_lang:
                target_lexicon=True

            if target_lexicon and "</Lexicon>" in buffer:
                
                new_id = syn_lang +"-gap-"+ langCode[0] +"new" + str(id_next("syn", 1))
                
                fileout.write("    <Synset id=\"" + new_id + "\" ili=\""+ new_ili +"\" lexicalized=\"false\" status=\"new\"></Synset>\n")
                fileout.write(buffer)

                target_lexicon=False
            else:
                fileout.write(buffer)
            buffer=filein.readline()

        filein.close()
        fileout.close()

        if new_id!="":
            new_synset={}

            new_synset["ili"]=new_ili
            new_synset["lexicalized"]="false"
            new_synset["pos"]=synsets[source_id]["pos"]

            synsets[new_id]=new_synset

            source_lang=source_id.split("-")[0]
            
            if source_lang==langCode[0]:
                synsets[source_id][syn_lang]=new_id
            elif syn_lang==langCode[0]:
                synsets[new_id][source_lang]
            else:
                synsets[synsets[source_id]["ili"]][syn_lang]=new_id
        
        
        os.remove(file)
        os.rename(file[:-4]+"_tmp.xml",file)

    #add a completely new word as a translation of an existing one
    elif event.startswith("Add_synset_translation_"):

        source_id=event[len("Add_synset_translation_"):].split("_")[0]
        syn_id=event[len("Add_synset_translation_"):].split("_")[1]

        syn_lang=syn_id.split("-")[0]

        # deprecated
        # if "relations" in synsets[entry_id]:
        #     print(synsets[entry_id]["relations"])

        #     for synreltype in synsets[entry_id]["relations"]:

        #         target_code=syn_id.split("-")[0]
        #         source_code=entry_id.split("-")[0]

        #         print(synreltype)

        #         middle_term=""
        #         final_term=""
        #         for synrel in synsets[entry_id]["relations"][synreltype]:
        #             print(synrel)

        #         if source_code!=langCode[0]:
        #             middle_term=synsets[synrel["ili"]]
        #         else:
        #             middle_term=synrel

        #         if target_code!=langCode[0]:
        #             if target_code in synsets[middle_term]:
        #                 final_term=synsets[middle_term][target_code]
        #         else:
        #             final_term=middle_term

        #         if final_term!="":
        #             print("something")


        new_gloss=sg.popup_get_text("Insert gloss")
        
        if new_gloss==None:
            continue

        new_gloss=new_gloss.strip()

        found=has_illegal_characters(new_gloss)
        if found:
            illegal_characters_popup()
            continue

        new_sense=sg.popup_get_text("Insert word")

        if new_sense==None:
            continue

        new_sense=new_sense.strip()

        found=has_illegal_characters(new_sense)
        if found:
            illegal_characters_popup()
            continue

        else:
            new_id=""
            new_ili=""

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

            buffer=filein.readline()

            while buffer!="":

                if "<Lexicon " in buffer:

                    current_language=buffer.strip().split(" ")[3].split("\"")[1]
                    fileout.write(buffer)

                    if current_language==syn_lang:
                        buffer=filein.readline()
                        while not buffer=="  </Lexicon>\n":
                            fileout.write(buffer)

                            buffer=filein.readline()

                        new_id=syn_lang + "-synnew" + str(id_next("syn",1))

                        if syn_lang==langCode[0]:
                            new_ili="new" + str(id_next("ili",1)) + "-" + synsets[source_id]["pos"]
                        else:
                            if source_id.split("-")[0]==langCode[0]:
                                new_ili=source_id
                            else:
                                new_ili=synsets[source_id]["ili"]

                        fileout.write("    <Synset id=\"" + new_id + "\" ili=\"" + new_ili + "\" partOfSpeech=\"" + synsets[source_id]["pos"] + "\" lexicalized=\"true\" status=\"new\">\n")
                        fileout.write("      <Definition language=\"" + syn_lang + "\" status=\"new\">" + new_gloss + "</Definition>\n")
                        fileout.write("    </Synset>\n")
                        fileout.write("  </Lexicon>\n")

                else:
                    fileout.write(buffer)

                buffer=filein.readline()
            
            filein.close()
            fileout.close()

            os.remove(file)
            os.rename(file[:-4]+"_tmp.xml",file)

            new_synset={}

            new_synset["ili"]=new_ili
            new_synset["lexicalized"]="true"
            new_synset["pos"]=synsets[source_id]["pos"]
            new_synset["gloss"]="[" + syn_lang + "] " + new_gloss
            new_synset["gloss_status"]="new"
            new_synset["status"]="new"

            synsets[new_id]=new_synset

            source_lang=source_id.split("-")[0]
            
            if source_lang==langCode[0]:
                synsets[source_id][syn_lang]=new_id
            elif syn_lang==langCode[0]:
                synsets[new_id][source_lang]
            else:
                synsets[synsets[source_id]["ili"]][syn_lang]=new_id

            add_sense(new_sense, new_id, file)
    
    # adds a translation to a synset as a lexical gap
    elif event.startswith("Add_lexical_gap_"):

        source_id=event[len("Add_lexical_gap_"):].split("_")[0]
        syn_lang=event[len("Add_lexical_gap_"):].split("_")[1]

        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        buffer=filein.readline()

        new_id=""
        new_ili=""
        current_language=""
        while buffer!="":

            if "<Lexicon " in buffer:
                current_language=buffer.strip().split(" ")[3].split("\"")[1]
                fileout.write(buffer)

                if current_language==syn_lang:
                    buffer=filein.readline()
                    while not buffer=="  </Lexicon>\n":
                        fileout.write(buffer)

                        buffer=filein.readline()

                    new_id = syn_lang + "-synnew" + str(id_next("syn",1))
                    
                    if syn_lang==langCode[0]:
                        new_ili="new" + str(id_next("ili",1)) + "-" + synsets[source_id]["pos"]
                    else:
                        if source_id.split("-")[0]==langCode[0]:
                            new_ili=source_id
                        else:
                            new_ili=synsets[source_id]["ili"]

                    fileout.write("    <Synset id=\"" + new_id + "\" ili=\"" + new_ili + "\" partOfSpeech=\"" + synsets[source_id]["pos"] + "\" lexicalized=\"lexical_gap\" status=\"new\"></Synset>\n")
                    fileout.write(buffer)
            else:
                fileout.write(buffer)

            buffer=filein.readline()

        filein.close()
        fileout.close()


        new_synset={}
        new_synset["ili"]=new_ili
        new_synset["lexicalized"]="lexical_gap"
        new_synset["pos"]=synsets[source_id]["pos"]

        synsets[new_id]=new_synset

        source_lang=source_id.split("-")[0]
            
        if source_lang==langCode[0]:
            synsets[source_id][syn_lang]=new_id
        elif syn_lang==langCode[0]:
            synsets[new_id][source_lang]
        else:
            synsets[synsets[source_id]["ili"]][syn_lang]=new_id

        os.remove(file)
        os.rename(file[:-4]+"_tmp.xml",file)

    # untranslatable buttons ---------------------------------------------------------------------------------------------------------------------
    elif event.startswith("Untranslatable_info_"):
        sg.popup("A concept is untranslatable if there is no way to translate it without using a description", title="What does untranslatable mean?")
        continue

    #setting a synset to translatable while asking for gloss and word if neccessary
    elif event.startswith("Set_to_translatable_"):

        syn_id=event[len("Set_to_translatable_"):].split("_")[1]
        source_id=event[len("Set_to_translatable_"):].split("_")[0]

        syn_lang=syn_id.split("-")[0]

        new_gloss=""
        if not "gloss" in synsets[syn_id]:
            new_gloss=sg.popup_get_text("Insert gloss")

            if new_gloss==None:
                continue

            new_gloss=new_gloss.strip()

            found=has_illegal_characters(new_gloss)
            if found:
                illegal_characters_popup()
                continue

        new_sense=""    
        if not "senses" in synsets[syn_id]:
            new_sense=sg.popup_get_text("Insert word")

            if new_sense==None:
                continue

            new_sense=new_sense.strip()

            found=has_illegal_characters(new_sense)
            if found:
                illegal_characters_popup()
                continue


        
        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")
        
        buffer=filein.readline()

        while buffer!="":

            if "Synset id=\"" + syn_id + "\"" in buffer:

                lexical_value=synsets[syn_id]["lexicalized"]

                buffer=buffer.split("lexicalized=\"" + lexical_value + "\"")[0] + "lexicalized=\"true\"" + buffer.split("lexicalized=\"" + lexical_value + "\"")[1]

                if not "status" in buffer:
                    buffer=buffer.split("\">")[0] + "\" status=\"modified\"" + ">" + buffer.split("\">")[1]
                    synsets[syn_id]["status"]="modified"

                if not "pos" in synsets[syn_id]:
                    synsets[syn_id]["pos"]=synsets[source_id]["pos"]

                if not "partOfSpeech" in buffer:
                    buffer= buffer.split("lexicalized=\"")[0] + "partOfSpeech=\"" + synsets[source_id]["pos"] + "\" lexicalized=\"" + buffer.split("lexicalized=\"")[1]

                if "</Synset>" in buffer:
                    buffer= buffer.split("</Synset>")[0] + "\n"
                    
                    fileout.write(buffer)
                    fileout.write("      <Definition language=\"" + syn_lang + "\" status=\"new\">" + new_gloss + "</Definition>\n")
                    fileout.write("    </Synset>\n")
                else:
                    fileout.write(buffer)

            else:
                fileout.write(buffer)

            buffer=filein.readline()

        filein.close()
        fileout.close()
        
        os.remove(file)
        os.rename(file[:-4]+"_tmp.xml",file)

        synsets[syn_id]["lexicalized"]="true"

        if new_gloss!="":
            synsets[syn_id]["gloss"]= "[" + syn_lang + "] " + new_gloss
            synsets[syn_id]["gloss_status"]="new"

        if new_sense!="":
            add_sense(new_sense,syn_id,file)

    # set synset to lexical gap
    elif event.startswith("To_lexical_gap"):

        syn_id=event[len("To_lexical_gap"):].split("_")[1]
        source_id=event[len("To_lexical_gap"):].split("_")[0]

        filein=open(file,"r",encoding="utf8")
        fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

        buffer=filein.readline()

        while buffer!="":

            if "id=\"" + syn_id + "\"" in buffer:

                lexical_value=synsets[syn_id]["lexicalized"]
                
                buffer=buffer.split("lexicalized=\"" + lexical_value + "\"")[0] + "lexicalized=\"lexical_gap\"" + buffer.split("lexicalized=\"" + lexical_value + "\"")[1]
                if not "partOfSpeech" in buffer:
                    buffer= buffer.split("lexicalized=\"")[0] + "partOfSpeech=\"" + synsets[source_id]["pos"] + "\" lexicalized=\"" + buffer.split("lexicalized=\"")[1]
                    synsets[syn_id]["pos"]=synsets[source_id]["pos"]

                #buffer=buffer.split("id=\"" + syn_id + "\"")[0] + "id=\"" + syn_id + "-lexicalgap\"" + buffer.split("id=\"" + syn_id + "\"")[1]

                if not "status=\"" in buffer:
                    buffer=buffer.split("\">")[0] + "\" status=\"modified\">" + buffer.split("\">")[1]
                    synsets[syn_id]["status"]="modified"

                fileout.write(buffer)
            else:
                fileout.write(buffer)

            buffer=filein.readline()

        filein.close()
        fileout.close()

        synsets[syn_id]["lexicalized"]="lexical_gap"

        os.remove(file)
        os.rename(file[:-4]+"_tmp.xml",file)

    #Lexical gap buttons (shares most with other buttons)--------------------------------------------------------------------------------------------------------------------------
    elif event.startswith("Lexical_gap_info_"):
        sg.popup("A lexical gap is present when there does not exist a direct translation for a word but nonetheless does not require a description to be translated", title="What is a lexical gap?")
        continue

    # reverse a modification made to the Lexicons
    elif event.startswith("Undo_"):
        splitevent=event.split("_")
        if splitevent[1]=="Sense":

            undo_sense=splitevent[2]
            status=senses[undo_sense]["status"]

            if status=="deleted":
                add_sense(senses[undo_sense]["word"], senses[undo_sense]["synsetId"], file)
            elif status=="deleted-again":
                add_sense(senses[undo_sense]["word"],senses[undo_sense]["synsetId"], file)
            elif status=="new":

                #remove_sense(undo_sense, senses[undo_sense]["synsetId"], file)

                filein=open(file,"r",encoding="utf8")
                fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

                buffer=filein.readline()
                pos_LE=0
                delete_LE=False

                while buffer!="":
                    if "<LexicalEntry " in buffer:
                        pos_LE=filein.tell()
                    elif "id=\"" + undo_sense in buffer:
                        filein.seek(pos_LE)

                        sensecount=0

                        buffer=filein.readline()
                        while not "</LexicalEntry>" in buffer:
                            if "<Sense " in buffer:
                                sensecount+=1
                            buffer=filein.readline()
                        
                        if sensecount<=1:
                            delete_LE=True
                        break

                    buffer=filein.readline()

                filein.seek(0)

                buffer=filein.readline()

                while buffer!="":

                    if delete_LE and "<LexicalEntry " in buffer and filein.tell()==pos_LE:
                        while not "</LexicalEntry>" in buffer:
                            buffer=filein.readline()

                        buffer=filein.readline()

                    if not delete_LE and "id=\"" + undo_sense in buffer:
                        while not "</Sense>" in buffer:
                            buffer=filein.readline()
                            
                    else:
                        fileout.write(buffer)
                    buffer=filein.readline()

                filein.close()
                fileout.close()

                syn_id=senses[undo_sense]["synsetId"]
                undo_lemma=senses[undo_sense]["word"]

                #remove from lemmas and senses fields from synset
                synsets[syn_id]["lemmas"].remove(undo_lemma)
                synsets[syn_id]["senses"].remove(undo_sense)

                #remove from lemmas
                undo_lemma=senses[undo_sense]["word"]
                print(lemmas[undo_lemma])

                if delete_LE:
                    lemmas.pop(undo_lemma)
                else:
                    print("not delete_LE")
                    for wordAttr in lemmas[undo_lemma]:
                        if wordAttr["senseId"]==undo_sense:
                            print("reached, deleting" + str(undo_sense))
                            lemmas[undo_lemma].remove(wordAttr)

                            print(lemmas[undo_lemma],flush=True)

                            break


                #remove from senses
                senses.pop(undo_sense)
                

                os.remove(file)
                os.rename(file[:-4]+"_tmp.xml",file)

        elif splitevent[1]=="Gloss":
            undo_synsetid=splitevent[2]

            filein=open(original_file,"r",encoding="utf8")

            buffer=filein.readline()
            original_gloss=""
            while buffer!="":
                if "Synset id=\"" + undo_synsetid + "\"" in buffer:
                    buffer=filein.readline()
                    original_gloss=buffer.split(">")[1].split("<")[0]
                    break
                else:
                    buffer=filein.readline()

            filein.close()

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

            buffer=filein.readline()
            while buffer!="":
                if "Synset id=\"" + undo_synsetid + "\"" in buffer:
                    fileout.write(buffer)
                    buffer=filein.readline()

                    splitb=buffer.split(" status=\"modified\"")
                    buffer=splitb[0] + splitb[1]

                    buffer=buffer.split(">")[0] + ">" + original_gloss + "<" + buffer.split("<")[2]

                    fileout.write(buffer)
                    buffer=filein.readline()

                else:
                    fileout.write(buffer)
                    buffer=filein.readline()

            filein.close()
            fileout.close()

            gloss_lang=synsets[undo_synsetid]["gloss"].split("] ")[0]+"] "

            synsets[undo_synsetid]["gloss"]=gloss_lang + original_gloss
            synsets[undo_synsetid]["gloss_status"]="unmodified"

            os.remove(file)
            os.rename(file[:-4]+"_tmp.xml",file)


        elif splitevent[1]=="Lexicalization":
            undo_synsetid=splitevent[2]

            filein=open(original_file,"r",encoding="utf8")

            buffer=filein.readline()
            original_lexicalization=""
            while buffer!="":
                if "Synset id=\"" + undo_synsetid + "\"" in buffer:
                    original_lexicalization=buffer.split("lexicalized=\"")[1].split("\"")[0]
                    break
                else:
                    buffer=filein.readline()

            filein.close()

            filein=open(file,"r",encoding="utf8")
            fileout=open(file[:-4]+"_tmp.xml","w",encoding="utf8")

            buffer=filein.readline()
            while buffer!="":
                if "Synset id=\"" + undo_synsetid + "\"" in buffer:
                    splitb=buffer.split("lexicalized=\"")
                    buffer=splitb[0] + "lexicalized=\"" + original_lexicalization + "\"" + "\"".join(splitb[1].split("\"")[1:len(splitb[1].split("\""))])
                    splitb=buffer.split(" status=\"modified\"")
                    buffer=splitb[0] + splitb[1]

                    fileout.write(buffer)
                    buffer=filein.readline()

                else:
                    fileout.write(buffer)
                    buffer=filein.readline()

            filein.close()
            fileout.close()

            synsets[undo_synsetid]["lexicalized"]=original_lexicalization
            synsets[undo_synsetid]["status"]="unmodified"

            os.remove(file)
            os.rename(file[:-4]+"_tmp.xml",file)
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

            if synsets[synsetId]["lexicalized"]=="true" and not synsets[synsetId]["lexicalized"]=="lexical_gap":
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

            # lemmaList = ", ".join(entry["lemmas"])
            # lemmaList.strip()

            # wraplength=(window.size[0]/(2*11))
            # if wraplength<5:
            #     wraplength=5

            # for line in textwrap.wrap(lemmaList, wraplength):
            #     layoutRow = []
            #     layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
            #     entry_layout.append(layoutRow)

            # i=1
            # for lemma in entry["lemmas"]:
            #     if i!=len(entry["lemmas"]):
            #         lemma=lemma+", "
                
            #     bg_color=None

                # layoutRow.append(SText(lemma, font="Helvetica 12 bold", text_color="blue", background_color=bg_color))
                # i=i+1

            if visualize_modifications and synsets[entry["synsetId"]]["status"]!="unmodified":

                status=synsets[entry["synsetId"]]["status"]
                if status=="modified":
                    bg_color="yellow"
                elif status=="new":
                    bg_color="green"
                layoutRow.append(GLOSS_DISPLAY("Synset Lexicalization",bg_color))

                if  status=="modified":
                    layoutRow.append(sg.Button("Undo",key="Undo_Lexicalization_" + entry["synsetId"], pad=((0,3),(3,3))))

                entry_layout.append(layoutRow)
                layoutRow=[]

            i=1
            l=len(synsets[entry["synsetId"]]["senses"])
            wraplength=(window.size[0]/(2*11))
            rowlength=0
            for sense in synsets[entry["synsetId"]]["senses"]:

                if not senses[sense]["status"].startswith("deleted") or visualize_modifications:

                    lemma=senses[sense]["word"]

                    if i!=l:
                        lemma=lemma+", "

                    bg_color=None
                    button_length=0
                    if visualize_modifications:
                        if senses[sense]["status"]=="new":
                            bg_color="green"
                        elif senses[sense]["status"]=="deleted":
                            bg_color="red"
                        elif senses[sense]["status"]=="deleted-again":
                            bg_color="purple"

                        if senses[sense]["status"]!="unmodified":
                            Undo_button=sg.Button("Undo",key="Undo_Sense_" + sense + "_" + entry["synsetId"], pad=((0,3),(3,3)))
                            button_length=5

                    if rowlength + len(lemma) + button_length > wraplength:
                        entry_layout.append(layoutRow)
                        layoutRow=[]
                        rowlength=0

                    layoutRow.append(SText(lemma, font="Helvetica 12 bold", text_color="blue", background_color=bg_color))
                    if visualize_modifications and senses[sense]["status"]!="unmodified":
                        if  bg_color=="green" and len(synsets[entry["synsetId"]]["lemmas"])>1:
                            layoutRow.append(Undo_button)
                    rowlength+=len(lemma) + button_length
                i=i+1


            entry_layout.append(layoutRow)

            bg_color=None
            if "gloss_status" in synsets[entry["synsetId"]] and visualize_modifications:
                if synsets[entry["synsetId"]]["gloss_status"]=="modified":
                    bg_color="yellow"
                elif synsets[entry["synsetId"]]["gloss_status"]=="new":
                    bg_color="green"

            wraplength=int(window.size[0]/(2*10)-10)
            if wraplength<5:
                wraplength=5

            Undo_button=sg.Button("Undo",key="Undo_Gloss_" + entry["synsetId"], pad=((0,3),(3,3)))
            added_button=False
            if synsets[entry["synsetId"]]["gloss_status"]!="unmodified" and synsets[entry["synsetId"]]["gloss_status"]!="new":
                add_button=True
            else: add_button=False
            for line in textwrap.wrap(entry["gloss"],wraplength):
                
                layoutRow = []
                layoutRow.append(GLOSS_DISPLAY(line, background_color=bg_color))
                entry_layout.append(layoutRow)

                if visualize_modifications and add_button and len(line) < wraplength-6:
                    layoutRow.append(Undo_button)
                    added_button=True

            if visualize_modifications and add_button and not added_button:
                entry_layout.append([Undo_button])

            #finding the equivalent synset in the target language

            untranslatable=False
            missing_translation=False
            lexical_gap=False
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

                        if translated_synsetId != "" and visualize_modifications and synsets[translated_synsetId]["status"]!="unmodified":

                            status=synsets[translated_synsetId]["status"]
                            if status=="modified":
                                bg_color="yellow"
                            elif status=="new":
                                bg_color="green"
                            translated_layoutRow.append(GLOSS_DISPLAY("Synset Lexicalization",bg_color))

                            if  status=="modified":
                                translated_layoutRow.append(sg.Button("Undo",key="Undo_Lexicalization_" + translated_synsetId + "_" + entry["synsetId"], pad=((0,3),(3,3))))

                            translated_layout.append(translated_layoutRow)
                            translated_layoutRow=[]

                    if translated_synsetId != "" and not synsets[translated_synsetId]["lexicalized"]=="lexical_gap":
                        if  "lemmas" in synsets[translated_synsetId] and synsets[translated_synsetId]["lexicalized"]=="true":

                            

                            # translated_lemmaList=", ".join(synsets[translated_synsetId]["lemmas"])

                            # wraplength=(window.size[0]/(2*11))
                            # if wraplength<5:
                            #     wraplength=5

                            # for line in textwrap.wrap(translated_lemmaList, wraplength):
                            #     translated_layoutRow = []
                            #     translated_layoutRow.append(SText(line, font="Helvetica 12 bold", text_color="blue"))
                            #     translated_layout.append(translated_layoutRow)

                            i=1
                            l=len(synsets[translated_synsetId]["senses"])
                            wraplength=(window.size[0]/(2*11))
                            rowlength=0
                            for sense in synsets[translated_synsetId]["senses"]:

                                if senses[sense]["status"]!="deleted" or visualize_modifications:

                                    lemma=senses[sense]["word"]

                                    if i!=l:
                                        lemma=lemma+", "

                                    bg_color=None
                                    button_length=0
                                    if visualize_modifications:
                                        if senses[sense]["status"]=="new":
                                            bg_color="green"
                                        elif senses[sense]["status"]=="deleted":
                                            bg_color="red"
                                        elif senses[sense]["status"]=="deleted-again":
                                            bg_color="purple"

                                    if senses[sense]["status"]!="unmodified":
                                        Undo_button=sg.Button("Undo",key="Undo_Sense_" + sense + "_" + translated_synsetId, pad=((0,3),(3,3)))
                                        button_length=5

                                    if rowlength + len(lemma) + button_length > wraplength:
                                        translated_layout.append(translated_layoutRow)
                                        translated_layoutRow=[]
                                        rowlength=0

                                    translated_layoutRow.append(SText(lemma, font="Helvetica 12 bold", text_color="blue", background_color=bg_color))
                                    if visualize_modifications and senses[sense]["status"]!="unmodified":
                                        if  bg_color=="green" and len(synsets[translated_synsetId]["lemmas"])>1:
                                            translated_layoutRow.append(Undo_button)
                                    rowlength+=len(lemma) + button_length
                                i=i+1

                            translated_layout.append(translated_layoutRow)

                            bg_color=None
                            if "gloss_status" in synsets[translated_synsetId] and visualize_modifications:
                                if synsets[translated_synsetId]["gloss_status"]=="modified":
                                    bg_color="yellow"
                                elif synsets[translated_synsetId]["gloss_status"]=="new":
                                    bg_color="green"

                            wraplength=int(window.size[0]/(2*10))
                            if wraplength<5:
                                wraplength=5

                            Undo_button=sg.Button("Undo",key="Undo_Gloss_" + translated_synsetId + "_" + entry["synsetId"], pad=((0,3),(3,3)))
                            added_button=False
                            if synsets[translated_synsetId]["gloss_status"]!="unmodified" and synsets[translated_synsetId]["gloss_status"]!="new":
                                add_button=True
                            else: add_button=False
                            for line in textwrap.wrap(synsets[translated_synsetId]["gloss"],wraplength):
                            
                                translated_layoutRow = []
                                translated_layoutRow.append(GLOSS_DISPLAY(line,bg_color))
                                translated_layout.append(translated_layoutRow)

                                if visualize_modifications and add_button and len(line) < wraplength-6:
                                    translated_layoutRow.append(Undo_button)
                                    added_button=True

                            if visualize_modifications and add_button and not added_button:
                                entry_layout.append([Undo_button])

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
                                    if "relations" in senses[sense] and not senses[sense]["status"].startswith("deleted"):
                                        for relation_type in senses[sense]["relations"]:
                                            #print(relation_type+str(senses[sense]["relations"][relation_type]))
                                            collapsableSection=[]

                                            for relation_target in senses[sense]["relations"][relation_type]:

                                                # print(relation_target)
                                                # print("translatedsynsetId: "+translated_synsetId)
                                                if not senses[relation_target]["status"].startswith("deleted"):
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
                            
                            untranslatable=True
                    else:
                        if translated_synsetId!="":
                            lexical_gap=True
            
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
                                if not senses[relation_target]["status"].startswith("deleted"):
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
    

            # appending the appropriate buttons

            translated_column_key=""
            if untranslatable:

                Untranslatable_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + translated_synsetId, pad=((0,3),(3,3)))
                translated_layout.append([sg.Text("Untranslatable", font="Helvetica 12"), Untranslatable_info])
                
                Set_translatable_button=sg.Button("Add word", key="Set_to_translatable_" + entry["synsetId"] + "_" + translated_synsetId)
                
                Set_lexical_gap_button=sg.Button("Set to lexical gap", key="To_lexical_gap" + entry["synsetId"] + "_" + translated_synsetId, pad=((3,0),(3,3)))
                Lexical_gap_info=sg.Button("ℹ", key="Lexical_gap_info_" + entry["synsetId"] + "_" + translated_synsetId, pad=((0,3),(3,3)))

                translated_layout.append([Set_translatable_button, Set_lexical_gap_button, Lexical_gap_info])
                
            elif missing_translation:

                translated_layout.append([sg.Text("Missing translation", font="Helvetica 12")])
                
                Missing_translation_button=sg.Button("Add translation", key="Add_synset_translation_" + entry["synsetId"] + "_" + target_code)
                Set_untranslatable_button=sg.Button("Set as untranslatable",key="Set_nodata_to_untranslatable_" + entry["synsetId"] + "_" + target_code, pad=((3,0),(3,3)))
                Untranslatable_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + target_code, pad=((0,3),(3,3)))
                Add_Lexical_gap=sg.Button("Add lexical gap", key="Add_lexical_gap_" + entry["synsetId"] + "_" + target_code, pad=((3,0),(3,3)))
                Lexical_gap_info=sg.Button("ℹ", key="Lexical_gap_info_" + entry["synsetId"], pad=((0,3),(3,3)))

                translated_layout.append([Missing_translation_button, Set_untranslatable_button, Untranslatable_info, Add_Lexical_gap, Lexical_gap_info])

            elif lexical_gap:
                Lexical_gap_info=sg.Button("ℹ", key="Lexical_gap_info_" + entry["synsetId"] + "_" + translated_synsetId, pad=((0,3),(3,3)))
                translated_layout.append([sg.Text("Lexical gap", font="Helvetica 12"), Lexical_gap_info])

                To_translatable_button=sg.Button("Remove lexical gap", key="Set_to_translatable_" + entry["synsetId"] + "_" + translated_synsetId)
                To_untranslatble_button=sg.Button("Set to untranslatable", key="Delexicalize_" + entry["synsetId"] + "_" + translated_synsetId, pad=((3,0),(3,3)))
                Untranslatable_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + target_code, pad=((0,3),(3,3)))

                translated_layout.append([To_translatable_button, To_untranslatble_button, Untranslatable_info])

            elif not (same_language or not tranlation_present):

                Gloss_correction_button_tranlslation=sg.Button("Correct gloss", key="Correct_gloss_" + entry["synsetId"] + "_" + translated_synsetId)
                Add_synonym_button_translation=sg.Button("Add synonym", key="Add_sense_to_synset_" + entry["synsetId"] + "_" + translated_synsetId)
                buttonrow=[Gloss_correction_button_tranlslation, Add_synonym_button_translation]
                if  len(synsets[translated_synsetId]["lemmas"])>1:
                    Remove_synonym_button_translation=sg.Button("Remove synonym", key="Remove_sense_from_synset_" + entry["synsetId"] + "_" + translated_synsetId)
                    buttonrow.append(Remove_synonym_button_translation)
                
                if translated_synsetId.split("-")[0]!=langCode[0]:
                    To_untranslatble_button=sg.Button("Set to untranslatable", key="Delexicalize_" + entry["synsetId"] + "_" + translated_synsetId, pad=((3,0),(3,3)))
                    buttonrow.append(To_untranslatble_button)
                    Untranslatable_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + target_code, pad=((0,3),(3,3)))
                    buttonrow.append(Untranslatable_info)

                    To_lexical_gap_button=sg.Button("Set to lexical gap", key="To_lexical_gap" + entry["synsetId"] + "_" + translated_synsetId, pad=((3,0),(3,3)))
                    Lexical_gap_info=sg.Button("ℹ", key="Untranslatable_info_" + entry["synsetId"] + "_" + target_code, pad=((0,3),(3,3)))
                    buttonrow.append(To_lexical_gap_button)
                    buttonrow.append(Lexical_gap_info)

                translated_layout.append(buttonrow)

            
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
    if visualize_modifications:
        vb_color="green"
    else: vb_color="red"
    newLayout = [
                 [sg.Text('Multi-LiveLanguage Lexicon  Hub:[' + langCode[0] + ']', font='Verdana 14 bold'), sg.Text('Language to translate to:', font='Verdana 12'), sg.OptionMenu(lang_selection, key="-Selected language-",default_value=values["-Selected language-"]), sg.Button("Visualize modifications",key="-Visualize_modifications-", button_color=vb_color)],
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