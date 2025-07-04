//+------------------------------------------------------------------+
//|                                                 Trade_Sender.mq5 |
//|                                  Copyright 2025, MetaQuotes Ltd. |
//|                                             https://www.mql5.com |
//+------------------------------------------------------------------+
//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
input string ServerURL = "http://127.0.0.1:5000/api/trades"; // Server Endpoint
input int Timeout = 5000;
input double Size_Multiple = 1.0; // Lot Size multiplier


struct TradeMap {
   ulong mt5Ticket;
   string browserTradeID;
   double takeProfit;
   double stopLoss;
};

TradeMap openTrades[];

int OnInit()
  {
//---
   Print("Trader_Sender EA initializing...");
//---
   return(INIT_SUCCEEDED);
  }
//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
//---
   
  }
//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
    if (PositionsTotal() == 0 && openTrades.Size() == 0)
    {
        // No trades opened, and tracking nothing
        return;
    }
    else
    { 
      // Either open and/or tracked trades
      
      if(openTrades.Size() > 0)
      {
         // First check if any tracked trades have closed
         if(CleanupClosedTrades())
            return;
            
         for (int i = 0; i < ArraySize(openTrades); i++)
         {
            // And then check for modifications
            CheckForModifications(openTrades[i].mt5Ticket);
         }
      }
      
      // Now check the open positions are all sent
      for(int i = 0; i < PositionsTotal(); i++)
      {
         ulong ticket = PositionGetTicket(i);
         if(!IsPositionSent(ticket))
            SendRequest_Trade(ticket);   
      }     
    }
  }
//+------------------------------------------------------------------+

void SendRequest_Trade(ulong ticket)
{
   if (PositionSelectByTicket(ticket))
   {
   
      // Extract position details
      string action = "trade";
      string symbol = PositionGetString(POSITION_SYMBOL);
      double volume = PositionGetDouble(POSITION_VOLUME) * Size_Multiple;
      double takeProfit = PositionGetDouble(POSITION_TP);
      double stopLoss = PositionGetDouble(POSITION_SL);
      string tradeDirection = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      
      // Prepare JSON data (only include values if they are valid)
      string jsonData = "{\"action\": \"" + action + "\"";
      jsonData += ", \"symbol\":  \"" + symbol + "\""; 
      jsonData += ", \"ticket\": " + (string)ticket;
      jsonData += ", \"direction\": \"" + tradeDirection + "\"";                
      jsonData += ", \"volume\": " + DoubleToString(volume, 5);      
      jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
      jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

      // Close the JSON object
      jsonData += "}";

      Print("Sending position: ", jsonData);

      // Convert JSON string to char array
      uchar jsonDataArray[];
      StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

      // Set headers
      string headers = "Content-Type: application/json\r\n";

      // Response buffers
      char result[];
      string resultHeaders = "";

      // Send HTTP POST request
      int responseCode = WebRequest(
         "POST",               // HTTP method
         ServerURL,            // URL
         headers,              // Headers
         Timeout,              // Timeout in milliseconds
         jsonDataArray,        // HTTP message body
         result,               // Server response
         resultHeaders         // Response headers
      );
    
      // Handle the response
      if (responseCode == -1)
      {
         Print("WebRequest failed: ", GetLastError());
      }
      else
      {
         Print("Response code: ", responseCode);
         Print("Server response: ", CharArrayToString(result));
         string browserID;
         ParseJSON(CharArrayToString(result), "", browserID);
         MarkPositionAsSent(ticket, browserID, takeProfit, stopLoss);
      }
   }
}

void SendRequest_Modify(ulong ticket)
{
   if (PositionSelectByTicket(ticket))
   {
      TradeMap entry;
      RetreiveTradeFromMap(ticket, entry);
   
      // Extract position details
      string action = "modify";
      string symbol = PositionGetString(POSITION_SYMBOL);
      double volume = PositionGetDouble(POSITION_VOLUME) * Size_Multiple;
      double takeProfit = 0.0;
      if(entry.takeProfit != PositionGetDouble(POSITION_TP))
         takeProfit = PositionGetDouble(POSITION_TP);
      double stopLoss = 0.0;
      if(entry.stopLoss != PositionGetDouble(POSITION_SL))
         stopLoss = PositionGetDouble(POSITION_SL);
      string tradeDirection = (PositionGetInteger(POSITION_TYPE) == POSITION_TYPE_BUY) ? "BUY" : "SELL";
      
      entry.takeProfit = PositionGetDouble(POSITION_TP);
      entry.stopLoss = PositionGetDouble(POSITION_SL);
      
      // Prepare JSON data
      string jsonData = "{\"action\": \"" + action + "\"";
      jsonData += ", \"symbol\":  \"" + symbol + "\""; 
      jsonData += ", \"ticket\": " + (string)ticket;
      jsonData += ", \"direction\": \"" + tradeDirection + "\"";                  
      jsonData += ", \"volume\": " + DoubleToString(volume, 5); 
      jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
      jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

      // Close the JSON object
      jsonData += "}";

      Print("Sending modification: ", jsonData);

      // Convert JSON string to char array
      uchar jsonDataArray[];
      StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

      // Set headers
      string headers = "Content-Type: application/json\r\n";

      // Response buffers
      char result[];
      string resultHeaders = "";

      // Send HTTP POST request
      int responseCode = WebRequest(
         "POST",               // HTTP method
         ServerURL,            // URL
         headers,              // Headers
         Timeout,              // Timeout in milliseconds
         jsonDataArray,        // HTTP message body
         result,               // Server response
         resultHeaders         // Response headers
      );
    
      // Handle the response
      if (responseCode == -1)
      {
         Print("WebRequest failed: ", GetLastError());
      }
      else
      {
         Print("Response code: ", responseCode);
         Print("Server response: ", CharArrayToString(result));
         UpdateMapEntry(ticket, entry);
      }
   }
}

void SendRequest_Delete(ulong ticket)
{
   string action = "delete";
   string symbol = "NONE";
   double volume = 0.0;
   double takeProfit = 0.0;
   double stopLoss = 0.0;
   string tradeDirection = "NONE";
   // Prepare JSON data (only include values if they are valid)
   string jsonData = "{\"action\": \"" + action + "\"";
   jsonData += ", \"symbol\":  \"" + symbol + "\""; 
   jsonData += ", \"ticket\": " + (string)ticket;
   jsonData += ", \"direction\": \"" + tradeDirection + "\"";                            
   jsonData += ", \"volume\": " + DoubleToString(volume, 5);     
   jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
   jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

   // Close the JSON object
   jsonData += "}";

   // Convert JSON string to char array
   uchar jsonDataArray[];
   StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

   // Set headers
   string headers = "Content-Type: application/json\r\n";

   // Response buffers
   char result[];
   string resultHeaders = "";
   
   Print("Sending delete: ", jsonData);

   // Send HTTP POST request
   int responseCode = WebRequest(
      "POST",               // HTTP method
      ServerURL,            // URL
      headers,              // Headers
      Timeout,              // Timeout in milliseconds
      jsonDataArray,        // HTTP message body
      result,               // Server response
      resultHeaders         // Response headers
   );
 
   // Handle the response
   if (responseCode == -1)
   {
      Print("WebRequest failed: ", GetLastError());
   }
   else
   {
      Print("Response code: ", responseCode);
      Print("Server response: ", CharArrayToString(result));
      RemoveTradeFromMap(ticket);
   }
}

void SendRequest_DeleteAll()
{
   string action = "delete_all";
   string symbol = "NONE";
   string ticket = "";
   double volume = 0.0;
   double takeProfit = 0.0;
   double stopLoss = 0.0;
   string tradeDirection = "NONE";
   // Prepare JSON data (only include values if they are valid)
   string jsonData = "{\"action\": \"" + action + "\"";
   jsonData += ", \"symbol\":  \"" + symbol + "\""; 
   jsonData += ",\"ticket\":\""     + ticket     + "\"";
   jsonData += ", \"direction\": \"" + tradeDirection + "\"";                            
   jsonData += ", \"volume\": " + DoubleToString(volume, 5);     
   jsonData += ", \"take_profit\": " + DoubleToString(takeProfit, 5);
   jsonData += ", \"stop_loss\": " + DoubleToString(stopLoss, 5);

   // Close the JSON object
   jsonData += "}";

   // Convert JSON string to char array
   uchar jsonDataArray[];
   StringToCharArray(jsonData, jsonDataArray, 0, StringLen(jsonData));

   // Set headers
   string headers = "Content-Type: application/json\r\n";

   // Response buffers
   char result[];
   string resultHeaders = "";
   
   Print("Sending delete_all: ", jsonData);

   // Send HTTP POST request
   int responseCode = WebRequest(
      "POST",               // HTTP method
      ServerURL,            // URL
      headers,              // Headers
      Timeout,              // Timeout in milliseconds
      jsonDataArray,        // HTTP message body
      result,               // Server response
      resultHeaders         // Response headers
   );
 
   // Handle the response
   if (responseCode == -1)
   {
      Print("WebRequest failed: ", GetLastError());
   }
   else
   {
      Print("Response code: ", responseCode);
      Print("Server response: ", CharArrayToString(result));
      ArrayFree(openTrades);
   }
}

// Function to check if a position has already been sent
bool IsPositionSent(ulong ticket)
{
   for (int i = ArraySize(openTrades) - 1; i >= 0; i--)
   {
      if (openTrades[i].mt5Ticket == ticket)
         return true;
   }
   return false;
}

void RetreiveTradeFromMap(ulong ticket, TradeMap &entry)
{
   for (int i = ArraySize(openTrades) - 1; i >= 0; i--)
   {
      if (openTrades[i].mt5Ticket == ticket)
      {
         entry = openTrades[i];
         return;
      }
   }
}

void RemoveTradeFromMap(ulong ticket)
{
   for (int i = ArraySize(openTrades) - 1; i >= 0; i--)
   {
      if (openTrades[i].mt5Ticket == ticket)
      {
         ArrayRemove(openTrades, i, 1);
         return;
      }
   }
}

void UpdateMapEntry(ulong ticket, TradeMap &entry)
{
   for (int i = 0; i < ArraySize(openTrades); i++)
   {
      if (openTrades[i].mt5Ticket == ticket)
      {
         openTrades[i] = entry;
         return;
      }
   }
}

// Function to mark a position as sent
void MarkPositionAsSent(ulong ticket, string id, double tp, double sl)
{
   TradeMap entry;
   entry.mt5Ticket = ticket;
   entry.browserTradeID = id;
   entry.takeProfit = tp;
   entry.stopLoss = sl;
   
   ArrayResize(openTrades, ArraySize(openTrades) + 1);
   openTrades[ArraySize(openTrades) - 1] = entry;
}


// Helper function to parse JSON response
bool ParseJSON(string jsonString, string key, string &value) {
   int keyPos = StringFind(jsonString, "\"" + key + "\":\"");
   if (keyPos == -1) return false;
   int startPos = keyPos + StringLen(key) + 3;
   int endPos = StringFind(jsonString, "\"", startPos);
   if (endPos == -1) return false;
   value = StringSubstr(jsonString, startPos, endPos - startPos);
   return true;
}


// Function to check and send modified trades
void CheckForModifications(ulong ticket)
{
   if(PositionSelectByTicket(ticket))
   {
      // Get the current take profit and stop loss values
      double currentTakeProfit = PositionGetDouble(POSITION_TP);
      double currentStopLoss = PositionGetDouble(POSITION_SL);
      
      TradeMap entry;
      RetreiveTradeFromMap(ticket, entry);
      
      if(entry.takeProfit != currentTakeProfit || entry.stopLoss != currentStopLoss)
      {
          // If either TP or SL has changed, log the modification and send the updated data
          Print("Trade modified: ", ticket);
          Print("Old TP: ", entry.takeProfit, " -> New TP: ", currentTakeProfit);
          Print("Old SL: ", entry.stopLoss, " -> New SL: ", currentStopLoss);
          
          // Send the updated data
          SendRequest_Modify(ticket);
      }
   }
}


bool CleanupClosedTrades()
{
   bool anyTradeRemoved = false;
   // First check if we have had all trades removed
   // Check if no open positions but tracking open trades
   int total_pos = PositionsTotal();
   if(total_pos == 0 && ArraySize(openTrades) > 1)
   {
      // Send a delete all request
      anyTradeRemoved = true;
      SendRequest_DeleteAll();
      Print("All trades closed");
      return anyTradeRemoved;    
   }

   
    for (int i = ArraySize(openTrades) - 1; i >= 0; i--) // Loop through open trades in reverse
    {
        ulong ticket = openTrades[i].mt5Ticket;
        
        // Check if the trade is still open
        bool isStillOpen = false;
        for (int j = 0; j < PositionsTotal(); j++)
        {
            if (PositionGetTicket(j) == ticket)
            {
                isStillOpen = true;
                break;
            }
        }

        // If the trade is closed, remove it from the array
        if (!isStillOpen)
        {
            anyTradeRemoved = true;
            Print("Trade closed, removing from tracking: ", ticket);
            SendRequest_Delete(ticket);
        }
    }
    return anyTradeRemoved;
}